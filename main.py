import os
import time
import json
import requests
from utils.plugin_base import PluginBase
from WechatAPI import WechatAPIClient
from utils.decorators import *
from utils.logger import logger
from .mjapi import MidJourneyAPI
from .mjcache import ImageCache


class MidJourney(PluginBase):
    description = "MidJourney AI绘画插件"
    author = "mouxan (原作者), 重构者"
    version = "1.0.0"

    def __init__(self):
        super().__init__()
        # 初始化配置
        self.config = self._load_config()
        
        # 初始化API客户端
        self.mj_api = MidJourneyAPI(self.config)
        
        # 会话缓存
        self.sessions = {}
        
        # 用户数据
        self.user_data = self._load_user_data()
        
        # 插件状态
        self.is_active = True
        
        logger.info("[MJ] 插件已初始化")
    
    def _load_config(self):
        """加载配置文件"""
        default_config = {
            "mj_url": "",
            "mj_api_secret": "",
            "mj_tip": True,
            "mj_admin_password": "",
            "discordapp_proxy": "",
            "daily_limit": 3,
            "imagine_prefix": ["/i", "/mj"],
            "fetch_prefix": ["/f"],
            "up_prefix": ["/u"],
            "pad_prefix": ["/p"],
            "blend_prefix": ["/b"],
            "describe_prefix": ["/d"],
            "queue_prefix": ["/q"],
            "end_prefix": ["/e"],
            "reroll_prefix": ["/r"]
        }
        
        # 读取配置文件
        config_path = os.path.join(os.path.dirname(__file__), "config.toml")
        if os.path.exists(config_path):
            try:
                import toml
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = toml.load(f)
                    # 合并配置
                    for key, value in config.items():
                        default_config[key] = value
            except Exception as e:
                logger.error(f"[MJ] 加载配置文件失败: {e}")
        
        return default_config
    
    def _load_user_data(self):
        """加载用户数据"""
        data_path = os.path.join(os.path.dirname(__file__), "user_data.json")
        if os.path.exists(data_path):
            try:
                with open(data_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"[MJ] 加载用户数据失败: {e}")
        
        # 返回默认用户数据结构
        return {
            "admin_users": [],
            "white_groups": [],
            "white_users": [],
            "black_groups": [],
            "black_users": [],
            "usage_records": {}
        }
    
    def _save_user_data(self):
        """保存用户数据"""
        data_path = os.path.join(os.path.dirname(__file__), "user_data.json")
        try:
            with open(data_path, 'w', encoding='utf-8') as f:
                json.dump(self.user_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[MJ] 保存用户数据失败: {e}")
    
    def _get_user_info(self, message):
        """获取用户信息"""
        user_id = message.get("from_user_id", "")
        user_nickname = message.get("from_user_nickname", "用户")
        group_id = message.get("room_id", "")
        group_name = message.get("room_name", "")
        
        # 判断用户权限
        is_admin = user_id in self.user_data["admin_users"]
        is_white_user = user_id in self.user_data["white_users"]
        is_black_user = user_id in self.user_data["black_users"]
        is_white_group = group_id in self.user_data["white_groups"]
        is_black_group = group_id in self.user_data["black_groups"]
        
        return {
            "user_id": user_id,
            "user_nickname": user_nickname,
            "group_id": group_id,
            "group_name": group_name,
            "is_group": bool(group_id),
            "is_admin": is_admin,
            "is_white_user": is_white_user,
            "is_black_user": is_black_user,
            "is_white_group": is_white_group,
            "is_black_group": is_black_group
        }
    
    @on_text_message(priority=10)
    async def handle_text(self, bot: WechatAPIClient, message: dict):
        """处理文本消息"""
        content = message.get("content", "").strip()
        if not content:
            return
        
        # 获取用户信息
        user_info = self._get_user_info(message)
        self.mj_api.set_user(json.dumps(user_info))
        
        # 过滤黑名单用户和群组
        if not user_info["is_admin"]:
            if user_info["is_black_user"] or user_info["is_black_group"]:
                return
            
            # 非白名单群组不处理
            if user_info["is_group"] and not user_info["is_white_group"]:
                return
        
        # 检查插件状态
        if not self.is_active and not user_info["is_admin"]:
            return
        
        # 处理命令
        if content.startswith("/"):
            await self._process_command(bot, message, content, user_info)
    
    async def _process_command(self, bot, message, content, user_info):
        """处理命令"""
        session_id = f"{user_info['user_id']}_{user_info['group_id']}"
        
        # 检查命令前缀
        command_type, prompt = self._check_command_prefix(content)
        
        if command_type == "imagine":
            if not prompt:
                await bot.send_text(message, "请输入要绘制的描述文字")
                return
            
            # 清除会话
            if session_id in self.sessions:
                del self.sessions[session_id]
            
            # 提交绘图任务
            await self._imagine(bot, message, prompt, [])
            
        elif command_type == "up":
            if not prompt:
                await bot.send_text(message, "请输入任务ID")
                return
            
            # 清除会话
            if session_id in self.sessions:
                del self.sessions[session_id]
            
            # 处理放大/变换任务
            await self._up(bot, message, prompt)
            
        elif command_type == "pad":
            if not prompt:
                await bot.send_text(message, "请输入要绘制的描述文字进行开启垫图模式，然后发送一张或者多张图片")
                return
            
            # 创建垫图会话
            self.sessions[session_id] = ImageCache(session_id, "imagine", prompt)
            await bot.send_text(message, "✨ 垫图模式\n✏ 请再发送一张或者多张图片")
            
        elif command_type == "blend":
            # 创建混图会话
            self.sessions[session_id] = ImageCache(session_id, "blend", prompt)
            await bot.send_text(message, f"✨ 混图模式\n✏ 请发送两张或多张图片，然后输入['{self.config['end_prefix'][0]}']结束")
            
        elif command_type == "describe":
            # 创建识图会话
            self.sessions[session_id] = ImageCache(session_id, "describe", prompt)
            await bot.send_text(message, "✨ 识图模式\n✏ 请发送一张图片")
            
        elif command_type == "end":
            # 从会话中获取缓存的图片
            if session_id not in self.sessions:
                await bot.send_text(message, "请先输入指令开启绘图模式")
                return
            
            img_cache = self.sessions[session_id].get_cache()
            base64_array = img_cache["base64Array"]
            prompt = img_cache["prompt"]
            instruct = img_cache["instruct"]
            
            if instruct == 'imagine':
                if len(base64_array) < 1:
                    await bot.send_text(message, "✨ 垫图模式\n✏ 请发送一张或多张图片方可完成垫图")
                else:
                    await self._imagine(bot, message, prompt, base64_array)
                    del self.sessions[session_id]
            
            elif instruct == 'blend':
                if len(base64_array) < 2:
                    await bot.send_text(message, "✨ 混图模式\n✏ 请至少发送两张图片方可完成混图")
                else:
                    await self._blend(bot, message, base64_array)
                    del self.sessions[session_id]
        
        elif command_type == "fetch":
            if not prompt:
                await bot.send_text(message, "请输入任务ID")
                return
            
            # 获取任务信息
            await self._fetch(bot, message, prompt)
            
        elif command_type == "reroll":
            if not prompt:
                await bot.send_text(message, "请输入任务ID")
                return
            
            # 重新生成
            await self._reroll(bot, message, prompt)
            
        elif command_type == "queue":
            # 查询队列
            await self._queue(bot, message)
    
    def _check_command_prefix(self, content):
        """检查命令前缀"""
        for prefix_type, prefixes in self.config.items():
            if not prefix_type.endswith("_prefix"):
                continue
                
            command_type = prefix_type.replace("_prefix", "")
            for prefix in prefixes:
                if content.startswith(prefix):
                    prompt = content[len(prefix):].strip()
                    return command_type, prompt
        
        return None, None
    
    async def _imagine(self, bot, message, prompt, base64_array):
        """提交绘图任务"""
        success, msg, task_id = self.mj_api.imagine(prompt, base64_array)
        await bot.send_text(message, msg)
    
    async def _up(self, bot, message, task_id):
        """处理放大/变换任务"""
        success, msg, new_task_id = self.mj_api.simpleChange(task_id)
        await bot.send_text(message, msg)
    
    async def _blend(self, bot, message, base64_array, dimensions=""):
        """处理混图任务"""
        success, msg, task_id = self.mj_api.blend(base64_array, dimensions)
        await bot.send_text(message, msg)
    
    async def _describe(self, bot, message, base64):
        """处理识图任务"""
        success, msg, task_id = self.mj_api.describe(base64)
        await bot.send_text(message, msg)
    
    async def _fetch(self, bot, message, task_id):
        """获取任务信息"""
        success, msg, image_url = self.mj_api.fetch(task_id)
        if success and image_url:
            await bot.send_text(message, msg)
            await bot.send_image_url(message, image_url)
        else:
            await bot.send_text(message, msg)
    
    async def _reroll(self, bot, message, task_id):
        """重新生成"""
        success, msg, new_task_id = self.mj_api.reroll(task_id)
        await bot.send_text(message, msg)
    
    async def _queue(self, bot, message):
        """查询队列"""
        success, msg = self.mj_api.task_queue()
        await bot.send_text(message, msg)
    
    @on_image_message(priority=10)
    async def handle_image(self, bot: WechatAPIClient, message: dict):
        """处理图片消息"""
        user_info = self._get_user_info(message)
        
        # 过滤黑名单用户和群组
        if not user_info["is_admin"]:
            if user_info["is_black_user"] or user_info["is_black_group"]:
                return
            
            # 非白名单群组不处理
            if user_info["is_group"] and not user_info["is_white_group"]:
                return
        
        # 检查插件状态
        if not self.is_active and not user_info["is_admin"]:
            return
        
        session_id = f"{user_info['user_id']}_{user_info['group_id']}"
        
        # 检查是否有活动的会话
        if session_id not in self.sessions:
            return
        
        # 获取图片
        img_url = message.get("image_url", "")
        if not img_url:
            return
        
        try:
            # 下载图片并转为base64
            response = requests.get(img_url, timeout=10)
            if response.status_code != 200:
                await bot.send_text(message, "下载图片失败")
                return
            
            import base64
            img_base64 = base64.b64encode(response.content).decode('utf-8')
            
            # 添加到缓存
            self.sessions[session_id].add_image(img_base64)
            
            # 获取当前缓存信息
            cache = self.sessions[session_id].get_cache()
            instruct = cache["instruct"]
            
            if instruct == "describe" and len(cache["base64Array"]) == 1:
                # 识图模式直接提交
                await self._describe(bot, message, img_base64)
                del self.sessions[session_id]
            else:
                # 提示当前状态
                count = len(cache["base64Array"])
                if instruct == "imagine":
                    await bot.send_text(message, f"✅ 已添加第{count}张图片\n✏ 继续发送图片或输入['{self.config['end_prefix'][0]}']结束")
                elif instruct == "blend":
                    await bot.send_text(message, f"✅ 已添加第{count}张图片\n✏ 继续发送图片或输入['{self.config['end_prefix'][0]}']结束")
        
        except Exception as e:
            logger.error(f"[MJ] 处理图片失败: {e}")
            await bot.send_text(message, f"处理图片失败: {str(e)}") 