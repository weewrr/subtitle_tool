import os
import re
import threading
import requests
import json

from backend.config.settings import Config

# LLM/翻译 API 请求超时(秒):连接 10s + 读取 120s(长文本生成需要余量)
HTTP_TIMEOUT = (10, 120)


class TranslationService:
    def __init__(self):
        self.translate_status = {
            'translating': False,
            'progress': 0,
            'status': 'idle',
            'error': None,
            'result': None
        }
    
    # 兜底清洗：小模型偶尔会把提示词里的时长上下文复述进译文开头，
    # 如「大约3.8秒的演讲时长。」「时长约为2.9秒。」——只剥离行首这类声明。
    _DURATION_LEAK_PATTERN = re.compile(
        r'^(?:大约|大約|时长|時長)?约?为?\s*\d+(?:\.\d+)?\s*(?:秒|秒钟|秒鐘)'
        r'[^，。；,;\n]*[，。；,;]?\s*'
    )

    @classmethod
    def _strip_duration_leak(cls, translated):
        """剥离译文行首泄漏的时长声明前缀；只匹配行首，避免误伤正文合法内容。"""
        if not translated or not isinstance(translated, str):
            return translated
        stripped = cls._DURATION_LEAK_PATTERN.sub('', translated, count=1)
        return stripped if stripped else translated

    def translate(self, text, from_lang, to_lang, engine='ollama', model='gemma3:1b',
                  prompt_template=None, temperature=0.0, max_tokens=2048, keep_formatting=True, task='translate',
                  duration=None, api_key=None):
        if engine == 'ollama':
            result = self._translate_with_ollama(text, from_lang, to_lang, model,
                                                 prompt_template, temperature, max_tokens, task,
                                                 duration=duration)
        elif engine == 'deepseek':
            ds_model = model if model and model != 'gemma3:1b' else 'deepseek-chat'
            result = self._translate_with_deepseek(text, from_lang, to_lang, ds_model, api_key,
                                                   prompt_template, temperature, max_tokens, task,
                                                   duration=duration)
        elif engine == 'bailian':
            bl_model = model if model and model != 'gemma3:1b' else 'qwen-plus'
            result = self._translate_with_bailian(text, from_lang, to_lang, bl_model, api_key,
                                                  prompt_template, temperature, max_tokens, task,
                                                  duration=duration)
        elif engine == 'deepL':
            result = self._translate_with_deepl(text, from_lang, to_lang)
        elif engine == 'google':
            result = self._translate_with_google(text, from_lang, to_lang)
        elif engine == 'chatgpt':
            result = self._translate_with_chatgpt(text, from_lang, to_lang,
                                                  prompt_template, temperature, max_tokens, task,
                                                  duration=duration)
        elif engine == 'anthropic':
            result = self._translate_with_anthropic(text, from_lang, to_lang,
                                                    prompt_template, temperature, max_tokens, task,
                                                    duration=duration)
        elif engine == 'gemini':
            result = self._translate_with_gemini(text, from_lang, to_lang,
                                                 prompt_template, temperature, max_tokens, task,
                                                 duration=duration)
        elif engine == 'mistral':
            result = self._translate_with_mistral(text, from_lang, to_lang,
                                                  prompt_template, temperature, max_tokens, task,
                                                  duration=duration)
        elif engine == 'libre':
            result = self._translate_with_libre(text, from_lang, to_lang)
        else:
            result = self._translate_with_ollama(text, from_lang, to_lang, model,
                                                 prompt_template, temperature, max_tokens, task,
                                                 duration=duration)

        # 输出侧兜底：剥离小模型可能复述进译文的时长声明
        if isinstance(result, dict) and result.get('translated') and not result.get('error'):
            result['translated'] = self._strip_duration_leak(result['translated'])
        return result
    
    # 默认「时长感知」翻译提示词。
    # duration 为软约束：让模型在已知可用朗读时间的情况下，
    # 主动选择更简洁、更口语化、仍准确自然的表达，而不是追求最短或硬凑字数。
    _DURATION_AWARE_TRANSLATE_PROMPT = (
        "Translate from {source_language} to {target_language}.\n\n"
        "[Context - for your reference only, NEVER include in the translation]\n"
        "The original speech duration is approximately {duration} seconds.\n\n"
        "Translate the text naturally and concisely, taking the available speaking time into consideration.\n\n"
        "Preserve the original meaning and all important information.\n"
        "Do not add information that is not present in the original text.\n"
        "Avoid unnecessary words, redundancy, and overly literal expressions.\n"
        "When multiple natural translations are possible, prefer the more concise expression when it better fits the available duration.\n\n"
        "The duration is a soft constraint, not an exact character limit.\n"
        "Do not sacrifice important meaning, accuracy, grammar, or naturalness just to make the translation shorter.\n\n"
        "Use natural expressions appropriate for the target language and context.\n\n"
        "Keep the original punctuation structure as much as possible, while allowing natural punctuation adjustments required by the target language.\n\n"
        "Do not censor the translation.\n\n"
        "CRITICAL: The duration and speaking time are internal context only. "
        "Your output must contain ONLY the translation of the text itself. "
        "NEVER mention, reference, or translate the duration, timing, or any meta-information "
        "(e.g. do NOT output phrases like 'about X seconds of speech').\n"
        "Give only the translated text without comments, explanations, notes, or labels.\n\n"
        "Text:\n{text}"
    )

    @staticmethod
    def _format_duration(duration):
        """把秒数格式化为干净字符串：3.0 -> '3'，3.6 -> '3.6'。"""
        if duration is None:
            return ''
        try:
            d = float(duration)
        except (TypeError, ValueError):
            return str(duration)
        if d == int(d):
            return str(int(d))
        return f'{d:.1f}'

    def _build_prompt(self, text, from_lang, to_lang, prompt_template, task='translate',
                      duration=None, duration_enabled=True):
        if task == 'split':
            if prompt_template:
                prompt = prompt_template.replace('{text}', text)
                return prompt
            return '''Split the following subtitle text into shorter segments for better readability.

IMPORTANT RULES:
1. Keep the EXACT original meaning - do NOT add, remove, or change any information
2. Split ONLY at natural break points (commas, conjunctions, etc.)
3. Each segment must be a grammatically complete phrase
4. Do NOT rephrase or rewrite any part of the text
5. Assign weight (1-10) based on segment length

Output ONLY a valid JSON array:
[
  {
    "message": "exact text from original",
    "weight": 5
  }
]

If the text is already appropriate as a single line, output it unchanged.

Original text:
''' + text
        
        if task == 'spell_check':
            if prompt_template:
                prompt = prompt_template.replace('{text}', text)
                return prompt
            return '''Check the spelling of the following subtitle text and correct any errors.

IMPORTANT RULES:
1. Fix ONLY actual spelling errors - do NOT change correct words
2. Preserve the original text structure and formatting
3. Keep proper nouns and names unchanged (people, places, brands, technical terms)
4. For each correction, provide the original word and the corrected word
5. If no errors found, return empty corrections array

Output ONLY a valid JSON object:
{
  "corrected_text": "the corrected full text",
  "corrections": [
    {
      "original": "misspelled word",
      "corrected": "corrected word"
    }
  ]
}

Text to check:
''' + text
        
        lang_names = {
            'en': 'English', 'zh': 'Chinese', 'ja': 'Japanese', 'ko': 'Korean',
            'english': 'English', 'chinese': 'Chinese', 'japanese': 'Japanese', 'korean': 'Korean'
        }
        from_name = lang_names.get(str(from_lang).lower(), from_lang)
        to_name = lang_names.get(str(to_lang).lower(), to_lang)

        if prompt_template:
            # 自定义提示词：同时兼容 {0}/{1}/{2} 与命名占位符
            dur_str = self._format_duration(duration)
            prompt = (prompt_template
                      .replace('{source_language}', from_name)
                      .replace('{target_language}', to_name)
                      .replace('{duration}', dur_str)
                      .replace('{0}', from_name)
                      .replace('{1}', to_name)
                      .replace('{2}', dur_str)
                      .replace('{text}', text))
            return prompt

        # 无自定义提示词：根据配置决定是否启用时长约束
        if duration_enabled and duration is not None:
            return self._DURATION_AWARE_TRANSLATE_PROMPT.format(
                source_language=from_name,
                target_language=to_name,
                duration=self._format_duration(duration),
                text=text
            )

        # 原始（向后兼容）默认提示词
        return f'Translate the following {from_name} text to {to_name}. Only output the translation result, nothing else.\n\n{text}'
    
    def _translate_with_ollama(self, text, from_lang, to_lang, model,
                               prompt_template=None, temperature=0.0, max_tokens=2048, task='translate',
                               duration=None):
        duration_enabled = getattr(Config, 'TRANSLATION_DURATION_CONSTRAINT_ENABLED', True)
        prompt = self._build_prompt(text, from_lang, to_lang, prompt_template, task,
                                    duration=duration, duration_enabled=duration_enabled)
        
        try:
            response = requests.post(
                'http://localhost:11434/api/chat',
                headers={'Content-Type': 'application/json'},
                json={
                    'model': model,
                    'messages': [
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ],
                    'stream': False,
                    'options': {
                        'temperature': temperature,
                        'num_predict': max_tokens
                    }
                },
                timeout=HTTP_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'translated': result.get('message', {}).get('content', text),
                    'engine': 'ollama',
                    'model': model
                }
            else:
                return {
                    'translated': text,
                    'engine': 'ollama',
                    'error': f'HTTP {response.status_code}: {response.text}'
                }
        except Exception as e:
            return {
                'translated': text,
                'engine': 'ollama',
                'error': str(e)
            }
    
    def _translate_with_deepl(self, text, from_lang, to_lang):
        api_key = os.environ.get('DEEPL_API_KEY')
        if not api_key:
            return {
                'translated': text,
                'engine': 'deepL',
                'error': 'DeepL API key not set'
            }
        
        try:
            response = requests.post(
                'https://api.deepl.com/v2/translate',
                headers={'Authorization': f'DeepL-Auth-Key {api_key}'},
                data={
                    'text': text,
                    'source_lang': from_lang.upper(),
                    'target_lang': to_lang.upper()
                },
                timeout=HTTP_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'translated': result.get('translations', [{}])[0].get('text', text),
                    'engine': 'deepL'
                }
            else:
                return {
                    'translated': text,
                    'engine': 'deepL',
                    'error': f'HTTP {response.status_code}: {response.text}'
                }
        except Exception as e:
            return {
                'translated': text,
                'engine': 'deepL',
                'error': str(e)
            }
    
    # 前端语言代码 → Google 语言代码(deep-translator 需要 zh-CN 形式)
    _GOOGLE_LANG_CODES = {
        'zh': 'zh-CN', 'zh-cn': 'zh-CN', 'zh-hans': 'zh-CN',
        'zh-tw': 'zh-TW', 'zh-hant': 'zh-TW',
        'en': 'en', 'ja': 'ja', 'ko': 'ko', 'auto': 'auto',
    }

    def _google_lang_code(self, lang):
        lang = str(lang or 'auto').strip()
        return self._GOOGLE_LANG_CODES.get(lang.lower(), lang)

    def _translate_with_google(self, text, from_lang, to_lang):
        # deep-translator:稳定的翻译客户端库(替代非官方 googletrans,后者长期不可用)
        try:
            from deep_translator import GoogleTranslator
        except ImportError:
            return {
                'translated': text,
                'engine': 'google',
                'error': 'deep-translator 未安装,请执行 pip install deep-translator'
            }

        try:
            translator = GoogleTranslator(
                source=self._google_lang_code(from_lang),
                target=self._google_lang_code(to_lang)
            )
            result = translator.translate(text)
            return {
                'translated': result,
                'engine': 'google'
            }
        except Exception as e:
            return {
                'translated': text,
                'engine': 'google',
                'error': str(e)
            }
    
    def _translate_with_chatgpt(self, text, from_lang, to_lang, 
                                prompt_template=None, temperature=0.0, max_tokens=2048, task='translate',
                                duration=None):
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            return {
                'translated': text,
                'engine': 'chatgpt',
                'error': 'OpenAI API key not set'
            }
        
        duration_enabled = getattr(Config, 'TRANSLATION_DURATION_CONSTRAINT_ENABLED', True)
        prompt = self._build_prompt(text, from_lang, to_lang, prompt_template, task,
                                    duration=duration, duration_enabled=duration_enabled)
        
        try:
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'gpt-3.5-turbo',
                    'messages': [
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ],
                    'temperature': temperature,
                    'max_tokens': max_tokens
                },
                timeout=HTTP_TIMEOUT
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    'translated': result.get('choices', [{}])[0].get('message', {}).get('content', text),
                    'engine': 'chatgpt'
                }
            else:
                return {
                    'translated': text,
                    'engine': 'chatgpt',
                    'error': f'HTTP {response.status_code}: {response.text}'
                }
        except Exception as e:
            return {
                'translated': text,
                'engine': 'chatgpt',
                'error': str(e)
            }
    
    def _translate_with_anthropic(self, text, from_lang, to_lang, 
                                  prompt_template=None, temperature=0.0, max_tokens=2048, task='translate',
                                  duration=None):
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            return {
                'translated': text,
                'engine': 'anthropic',
                'error': 'Anthropic API key not set'
            }
        
        duration_enabled = getattr(Config, 'TRANSLATION_DURATION_CONSTRAINT_ENABLED', True)
        prompt = self._build_prompt(text, from_lang, to_lang, prompt_template, task,
                                    duration=duration, duration_enabled=duration_enabled)
        
        try:
            response = requests.post(
                'https://api.anthropic.com/v1/messages',
                headers={
                    'x-api-key': api_key,
                    'Content-Type': 'application/json',
                    'anthropic-version': '2023-06-01'
                },
                json={
                    'model': 'claude-3-sonnet-20240229',
                    'messages': [
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ],
                    'max_tokens': max_tokens
                },
                timeout=HTTP_TIMEOUT
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    'translated': result.get('content', [{}])[0].get('text', text),
                    'engine': 'anthropic'
                }
            else:
                return {
                    'translated': text,
                    'engine': 'anthropic',
                    'error': f'HTTP {response.status_code}: {response.text}'
                }
        except Exception as e:
            return {
                'translated': text,
                'engine': 'anthropic',
                'error': str(e)
            }
    
    def _translate_with_gemini(self, text, from_lang, to_lang, 
                               prompt_template=None, temperature=0.0, max_tokens=2048, task='translate',
                               duration=None):
        api_key = os.environ.get('GOOGLE_API_KEY')
        if not api_key:
            return {
                'translated': text,
                'engine': 'gemini',
                'error': 'Google API key not set'
            }
        
        duration_enabled = getattr(Config, 'TRANSLATION_DURATION_CONSTRAINT_ENABLED', True)
        prompt = self._build_prompt(text, from_lang, to_lang, prompt_template, task,
                                    duration=duration, duration_enabled=duration_enabled)
        
        try:
            response = requests.post(
                f'https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash-lite:generateContent?key={api_key}',
                headers={'Content-Type': 'application/json'},
                json={
                    'contents': [
                        {
                            'parts': [
                                {
                                    'text': prompt
                                }
                            ]
                        }
                    ],
                    'generationConfig': {
                        'temperature': temperature,
                        'maxOutputTokens': max_tokens
                    }
                },
                timeout=HTTP_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'translated': result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', text),
                    'engine': 'gemini'
                }
            else:
                return {
                    'translated': text,
                    'engine': 'gemini',
                    'error': f'HTTP {response.status_code}: {response.text}'
                }
        except Exception as e:
            return {
                'translated': text,
                'engine': 'gemini',
                'error': str(e)
            }
    
    def _translate_with_mistral(self, text, from_lang, to_lang, 
                                prompt_template=None, temperature=0.0, max_tokens=2048, task='translate',
                                duration=None):
        api_key = os.environ.get('MISTRAL_API_KEY')
        if not api_key:
            return {
                'translated': text,
                'engine': 'mistral',
                'error': 'Mistral API key not set'
            }
        
        duration_enabled = getattr(Config, 'TRANSLATION_DURATION_CONSTRAINT_ENABLED', True)
        prompt = self._build_prompt(text, from_lang, to_lang, prompt_template, task,
                                    duration=duration, duration_enabled=duration_enabled)
        
        try:
            response = requests.post(
                'https://api.mistral.ai/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'mistral-medium-latest',
                    'messages': [
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ],
                    'temperature': temperature,
                    'max_tokens': max_tokens
                },
                timeout=HTTP_TIMEOUT
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    'translated': result.get('choices', [{}])[0].get('message', {}).get('content', text),
                    'engine': 'mistral'
                }
            else:
                return {
                    'translated': text,
                    'engine': 'mistral',
                    'error': f'HTTP {response.status_code}: {response.text}'
                }
        except Exception as e:
            return {
                'translated': text,
                'engine': 'mistral',
                'error': str(e)
            }
    
    def _translate_openai_compatible(self, text, from_lang, to_lang, engine_name, base_url, model,
                                     api_key, prompt_template, temperature, max_tokens, task, duration=None):
        """OpenAI 兼容 chat/completions 通用实现（DeepSeek / 阿里百炼等）"""
        if not api_key:
            return {
                'translated': text,
                'engine': engine_name,
                'error': f'{engine_name} API Key 未设置，请在翻译窗口中填写'
            }
        
        duration_enabled = getattr(Config, 'TRANSLATION_DURATION_CONSTRAINT_ENABLED', True)
        prompt = self._build_prompt(text, from_lang, to_lang, prompt_template, task,
                                    duration=duration, duration_enabled=duration_enabled)
        
        try:
            response = requests.post(
                f'{base_url}/chat/completions',
                headers={
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': model,
                    'messages': [
                        {
                            'role': 'user',
                            'content': prompt
                        }
                    ],
                    'temperature': temperature,
                    'max_tokens': max_tokens
                },
                timeout=HTTP_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'translated': result.get('choices', [{}])[0].get('message', {}).get('content', text),
                    'engine': engine_name,
                    'model': model
                }
            else:
                return {
                    'translated': text,
                    'engine': engine_name,
                    'model': model,
                    'error': f'HTTP {response.status_code}: {response.text}'
                }
        except Exception as e:
            return {
                'translated': text,
                'engine': engine_name,
                'error': str(e)
            }
    
    def _translate_with_deepseek(self, text, from_lang, to_lang, model, api_key,
                                 prompt_template=None, temperature=0.0, max_tokens=2048, task='translate',
                                 duration=None):
        api_key = api_key or os.environ.get('DEEPSEEK_API_KEY')
        return self._translate_openai_compatible(
            text, from_lang, to_lang, 'deepseek',
            'https://api.deepseek.com/v1', model, api_key,
            prompt_template, temperature, max_tokens, task, duration=duration
        )
    
    def _translate_with_bailian(self, text, from_lang, to_lang, model, api_key,
                                prompt_template=None, temperature=0.0, max_tokens=2048, task='translate',
                                duration=None):
        # 阿里百炼（DashScope）OpenAI 兼容模式
        api_key = api_key or os.environ.get('DASHSCOPE_API_KEY') or os.environ.get('BAILIAN_API_KEY')
        return self._translate_openai_compatible(
            text, from_lang, to_lang, 'bailian',
            'https://dashscope.aliyuncs.com/compatible-mode/v1', model, api_key,
            prompt_template, temperature, max_tokens, task, duration=duration
        )
    
    def _translate_with_libre(self, text, from_lang, to_lang):
        try:
            response = requests.post(
                'https://translate.argosopentech.com/translate',
                headers={'Content-Type': 'application/json'},
                json={
                    'q': text,
                    'source': from_lang,
                    'target': to_lang,
                    'format': 'text'
                },
                timeout=HTTP_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'translated': result.get('translatedText', text),
                    'engine': 'libre'
                }
            else:
                return {
                    'translated': text,
                    'engine': 'libre',
                    'error': f'HTTP {response.status_code}: {response.text}'
                }
        except Exception as e:
            return {
                'translated': text,
                'engine': 'libre',
                'error': str(e)
            }
    
    def translate_async(self, text, from_lang, to_lang, engine='ollama', model='gemma3:1b'):
        if self.translate_status['translating']:
            return {'error': '已有翻译任务正在进行中'}
        
        thread = threading.Thread(
            target=self._translate_thread,
            args=(text, from_lang, to_lang, engine, model)
        )
        thread.start()
        
        return {'message': '开始翻译'}
    
    def _translate_thread(self, text, from_lang, to_lang, engine, model):
        try:
            self.translate_status['translating'] = True
            self.translate_status['progress'] = 0
            self.translate_status['status'] = 'translating'
            self.translate_status['error'] = None
            
            result = self.translate(text, from_lang, to_lang, engine, model)
            
            self.translate_status['progress'] = 100
            self.translate_status['status'] = 'completed'
            self.translate_status['result'] = result
        except Exception as e:
            self.translate_status['status'] = 'error'
            self.translate_status['error'] = str(e)
        finally:
            self.translate_status['translating'] = False
    
    def get_status(self):
        return self.translate_status
    
    def get_result(self):
        if self.translate_status['result']:
            result = self.translate_status['result']
            self.translate_status['result'] = None
            return result
        return None
