from backend import create_app
from backend.config.settings import Config

app = create_app()

if __name__ == '__main__':
    print('启动字幕编辑工具后端服务...')
    print(f'访问 http://{Config.HOST}:{Config.PORT} 使用应用')
    app.run(debug=Config.DEBUG, use_reloader=False, host=Config.HOST, port=Config.PORT)
