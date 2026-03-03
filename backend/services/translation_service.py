import os
import sys
import subprocess
import threading
import requests
import json


class TranslationService:
    def __init__(self):
        self.translate_status = {
            'translating': False,
            'progress': 0,
            'status': 'idle',
            'error': None,
            'result': None
        }
    
    def translate(self, text, from_lang, to_lang, engine='ollama', model='gemma3:1b', 
              prompt_template=None, temperature=0.0, max_tokens=2048, keep_formatting=True, task='translate'):
        if engine == 'ollama':
            return self._translate_with_ollama(text, from_lang, to_lang, model, 
                                               prompt_template, temperature, max_tokens, task)
        elif engine == 'deepL':
            return self._translate_with_deepl(text, from_lang, to_lang)
        elif engine == 'google':
            return self._translate_with_google(text, from_lang, to_lang)
        elif engine == 'chatgpt':
            return self._translate_with_chatgpt(text, from_lang, to_lang, 
                                                prompt_template, temperature, max_tokens, task)
        elif engine == 'anthropic':
            return self._translate_with_anthropic(text, from_lang, to_lang, 
                                                  prompt_template, temperature, max_tokens, task)
        elif engine == 'gemini':
            return self._translate_with_gemini(text, from_lang, to_lang, 
                                               prompt_template, temperature, max_tokens, task)
        elif engine == 'mistral':
            return self._translate_with_mistral(text, from_lang, to_lang, 
                                                prompt_template, temperature, max_tokens, task)
        elif engine == 'libre':
            return self._translate_with_libre(text, from_lang, to_lang)
        else:
            return self._translate_with_ollama(text, from_lang, to_lang, model, 
                                               prompt_template, temperature, max_tokens, task)
    
    def _build_prompt(self, text, from_lang, to_lang, prompt_template, task='translate'):
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
        
        if prompt_template:
            prompt = prompt_template.replace('{0}', from_lang)
            prompt = prompt.replace('{1}', to_lang)
            prompt = prompt.replace('{text}', text)
            return prompt
        else:
            lang_names = {
                'en': 'English', 'zh': 'Chinese', 'ja': 'Japanese', 'ko': 'Korean',
                'english': 'English', 'chinese': 'Chinese', 'japanese': 'Japanese', 'korean': 'Korean'
            }
            from_name = lang_names.get(from_lang.lower(), from_lang)
            to_name = lang_names.get(to_lang.lower(), to_lang)
            return f'Translate the following {from_name} text to {to_name}. Only output the translation result, nothing else.\n\n{text}'
    
    def _translate_with_ollama(self, text, from_lang, to_lang, model, 
                               prompt_template=None, temperature=0.0, max_tokens=2048, task='translate'):
        try:
            import requests
        except ImportError:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'requests', '-q'])
            import requests
        
        prompt = self._build_prompt(text, from_lang, to_lang, prompt_template, task)
        
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
                }
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
                }
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
    
    def _translate_with_google(self, text, from_lang, to_lang):
        try:
            from googletrans import Translator
        except ImportError:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'googletrans==4.0.0-rc1', '-q'])
            from googletrans import Translator
        
        try:
            translator = Translator()
            result = translator.translate(text, src=from_lang, dest=to_lang)
            return {
                'translated': result.text,
                'engine': 'google'
            }
        except Exception as e:
            return {
                'translated': text,
                'engine': 'google',
                'error': str(e)
            }
    
    def _translate_with_chatgpt(self, text, from_lang, to_lang, 
                                prompt_template=None, temperature=0.0, max_tokens=2048, task='translate'):
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            return {
                'translated': text,
                'engine': 'chatgpt',
                'error': 'OpenAI API key not set'
            }
        
        prompt = self._build_prompt(text, from_lang, to_lang, prompt_template, task)
        
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
                }
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
                                  prompt_template=None, temperature=0.0, max_tokens=2048, task='translate'):
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            return {
                'translated': text,
                'engine': 'anthropic',
                'error': 'Anthropic API key not set'
            }
        
        prompt = self._build_prompt(text, from_lang, to_lang, prompt_template, task)
        
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
                }
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
                               prompt_template=None, temperature=0.0, max_tokens=2048, task='translate'):
        api_key = os.environ.get('GOOGLE_API_KEY')
        if not api_key:
            return {
                'translated': text,
                'engine': 'gemini',
                'error': 'Google API key not set'
            }
        
        prompt = self._build_prompt(text, from_lang, to_lang, prompt_template, task)
        
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
                }
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
                                prompt_template=None, temperature=0.0, max_tokens=2048, task='translate'):
        api_key = os.environ.get('MISTRAL_API_KEY')
        if not api_key:
            return {
                'translated': text,
                'engine': 'mistral',
                'error': 'Mistral API key not set'
            }
        
        prompt = self._build_prompt(text, from_lang, to_lang, prompt_template, task)
        
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
                }
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
                }
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
