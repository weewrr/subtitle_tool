import os
from backend.config.settings import Config
from backend.utils.file_utils import ensure_directory


class SubtitleFileService:
    @staticmethod
    def save_original_subtitle(srt_content, filename, overwrite=False):
        if not srt_content:
            return {'error': '字幕内容为空'}
        
        save_dir = ensure_directory(Config.ORIGINAL_SUBTITLE_DIR)
        
        if not filename.endswith('.srt'):
            filename += '.srt'
        
        filepath = os.path.join(save_dir, filename)
        
        if os.path.exists(filepath) and not overwrite:
            return {
                'exists': True,
                'message': f'文件 {filename} 已存在，是否覆盖？',
                'filepath': filepath
            }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            return {
                'success': True,
                'message': '保存成功',
                'filepath': filepath,
                'filename': filename
            }
        except Exception as e:
            return {'error': f'保存失败: {str(e)}'}

    @staticmethod
    def save_translation_subtitle(srt_content, filename, overwrite=False):
        if not srt_content:
            return {'error': '字幕内容为空'}
        
        save_dir = ensure_directory(Config.TRANSLATION_SUBTITLE_DIR)
        
        if not filename.endswith('.srt'):
            filename += '.srt'
        
        filepath = os.path.join(save_dir, filename)
        
        if os.path.exists(filepath) and not overwrite:
            return {
                'exists': True,
                'message': f'文件 {filename} 已存在，是否覆盖？',
                'filepath': filepath
            }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            return {
                'success': True,
                'message': '翻译字幕保存成功',
                'filepath': filepath,
                'filename': filename
            }
        except Exception as e:
            return {'error': f'保存失败: {str(e)}'}

    @staticmethod
    def auto_save_subtitle(srt_content, filename):
        if not srt_content:
            return {'error': '字幕内容为空'}
        
        save_dir = ensure_directory(Config.ORIGINAL_SUBTITLE_DIR)
        
        if not filename.endswith('.srt'):
            filename += '.srt'
        
        filepath = os.path.join(save_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            return {
                'success': True,
                'message': '自动保存成功',
                'filepath': filepath
            }
        except Exception as e:
            return {'error': f'自动保存失败: {str(e)}'}
