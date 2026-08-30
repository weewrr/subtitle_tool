from backend import create_app
from backend.config.settings import Config

app = create_app()

if __name__ == '__main__':
    print('启动字幕编辑工具后端服务...')
    print(f'访问 http://{Config.HOST}:{Config.PORT} 使用应用')
    if Config.DEBUG:
        # 开发模式:Flask 调试服务器
        app.run(debug=True, use_reloader=False, host=Config.HOST, port=Config.PORT)
    else:
        # 生产模式:waitress(纯 Python、Windows 友好、生产级 WSGI 服务器)
        from waitress import serve
        serve(app, host=Config.HOST, port=Config.PORT, threads=8)
