import os

from backend.config.settings import Config
from backend.utils.file_utils import ensure_directory, sanitize_filename


class SubtitleFileService:
    @staticmethod
    def _save_subtitle(srt_content, filename, overwrite, save_dir, success_message):
        """字幕保存共用实现:净化文件名防路径遍历,统一覆盖确认流程。"""
        if not srt_content:
            return {'error': '字幕内容为空'}

        filename = sanitize_filename(filename)
        if not filename:
            return {'error': '文件名不合法'}

        if not filename.endswith('.srt'):
            filename += '.srt'

        save_dir = ensure_directory(save_dir)
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
        except OSError as e:
            return {'error': f'保存失败: {e}'}

        return {
            'success': True,
            'message': success_message,
            'filepath': filepath,
            'filename': filename
        }

    @staticmethod
    def save_original_subtitle(srt_content, filename, overwrite=False):
        return SubtitleFileService._save_subtitle(
            srt_content, filename, overwrite, Config.ORIGINAL_SUBTITLE_DIR, '保存成功'
        )

    @staticmethod
    def save_translation_subtitle(srt_content, filename, overwrite=False):
        return SubtitleFileService._save_subtitle(
            srt_content, filename, overwrite, Config.TRANSLATION_SUBTITLE_DIR, '翻译字幕保存成功'
        )

    @staticmethod
    def auto_save_subtitle(srt_content, filename):
        # 自动保存总是直接覆盖,不做存在性确认
        return SubtitleFileService._save_subtitle(
            srt_content, filename, True, Config.ORIGINAL_SUBTITLE_DIR, '自动保存成功'
        )
