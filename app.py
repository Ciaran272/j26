"""
Flask应用主入口
采用应用工厂模式，模块化设计
"""
import logging
from flask import Flask
from flask_cors import CORS

from config import config
from api.routes import api_bp


def setup_logging() -> None:
    """配置日志系统"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('app.log', encoding='utf-8')
        ]
    )


def create_app(config_obj=None) -> Flask:
    """
    应用工厂函数
    
    Args:
        config_obj: 配置对象，如果为None则使用默认配置
        
    Returns:
        Flask应用实例
    """
    # 设置日志
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # 创建Flask应用
    app = Flask(
        __name__,
        static_folder=config.STATIC_FOLDER,
        static_url_path=config.STATIC_URL_PATH
    )
    
    # 加载配置
    if config_obj:
        app.config.from_object(config_obj)
    else:
        config.validate()
    
    # 配置CORS
    if config.CORS_ORIGINS == '*':
        CORS(app)
        logger.warning("⚠ CORS允许所有源，生产环境请设置CORS_ORIGINS")
    else:
        CORS(app, origins=config.CORS_ORIGINS.split(','))
        logger.info(f"✓ CORS配置完成: {config.CORS_ORIGINS}")
    
    # 注册蓝图
    app.register_blueprint(api_bp, url_prefix='/api')
    logger.info("✓ API蓝图注册完成")
    
    # 首页路由
    @app.route("/")
    def index():
        return app.send_static_file('index.html')
    
    # 健康检查端点（用于Docker健康检查和监控）
    @app.route("/health")
    def health():
        from flask import jsonify
        return jsonify({
            "status": "healthy",
            "service": "Japanese Furigana Generator",
            "timestamp": __import__('datetime').datetime.now().isoformat()
        })
    
    logger.info("=" * 50)
    logger.info("日语平假名注音器启动成功")
    logger.info(f"服务器地址: http://{config.HOST}:{config.PORT}")
    logger.info(f"调试模式: {config.DEBUG}")
    logger.info("=" * 50)
    
    return app


def main():
    """主函数"""
    app = create_app()
    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG
    )


if __name__ == "__main__":
    main()

