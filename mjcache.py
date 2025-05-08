class ImageCache:
    """图片缓存类，用于管理会话中的图片"""
    
    def __init__(self, session_id, instruct, prompt=""):
        """初始化图片缓存
        
        Args:
            session_id: 会话ID
            instruct: 指令类型（imagine/blend/describe）
            prompt: 提示词
        """
        self.session_id = session_id
        self.instruct = instruct  # 指令类型：imagine/blend/describe
        self.prompt = prompt  # 提示词
        self.base64Array = []  # 图片base64数组
        
    def add_image(self, img_base64):
        """添加图片到缓存
        
        Args:
            img_base64: 图片base64编码
        """
        if img_base64 and img_base64 not in self.base64Array:
            self.base64Array.append(img_base64)
    
    def get_cache(self):
        """获取缓存数据
        
        Returns:
            包含提示词、指令和图片数组的字典
        """
        return {
            "prompt": self.prompt,
            "instruct": self.instruct,
            "base64Array": self.base64Array
        }
    
    def reset(self):
        """重置缓存"""
        self.base64Array = [] 