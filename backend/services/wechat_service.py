"""微信服务封装。

封装两类场景：
1. 小程序登录：wx.login 拿到 code -> code2session 换取 openid / unionid。
2. 公众号二维码登录（预留）：get_access_token + get_qr_ticket 生成带场景值的二维码。

为支持本地开发与自动化测试，提供 WECHAT_MOCK 模式：未配置真实 AppID 或在 mock
模式下，code2session 返回确定性的 mock openid，不发起任何网络请求。
"""
import requests

from flask import current_app


class WeChatAPIError(Exception):
    """微信接口返回非预期结果。"""

    def __init__(self, detail=None):
        self.detail = detail
        super().__init__(str(detail))


class WeChatService:
    JSCODE2SESSION_URL = 'https://api.weixin.qq.com/sns/jscode2session'
    TOKEN_URL = 'https://api.weixin.qq.com/cgi-bin/token'
    QRCODE_URL = 'https://api.weixin.qq.com/cgi-bin/qrcode/create'

    def __init__(self, app_id, app_secret, mock=False):
        self.app_id = app_id
        self.app_secret = app_secret
        self.mock = mock

    # ---- 小程序登录 ----
    def code2session(self, code):
        """用 wx.login 的 code 换取 openid / unionid。

        返回 dict：{'openid': ..., 'unionid': ..., 'session_key': ...}
        """
        if self.mock:
            return {
                'openid': f'mock_openid_{code}',
                'unionid': f'mock_unionid_{code}',
                'session_key': 'mock_session_key',
            }

        if not self.app_id or not self.app_secret:
            raise WeChatAPIError('微信 AppID / AppSecret 未配置')

        params = {
            'appid': self.app_id,
            'secret': self.app_secret,
            'js_code': code,
            'grant_type': 'authorization_code',
        }
        try:
            resp = requests.get(self.JSCODE2SESSION_URL, params=params, timeout=10)
            data = resp.json()
        except requests.RequestException as e:  # noqa: F841
            raise WeChatAPIError('微信服务请求失败')

        if 'openid' not in data:
            raise WeChatAPIError(data)
        return data

    # ---- 公众号二维码登录（预留，桌面端后续可切换此模式） ----
    def get_access_token(self):
        if self.mock:
            return 'mock_access_token'
        params = {
            'grant_type': 'client_credential',
            'appid': self.app_id,
            'secret': self.app_secret,
        }
        resp = requests.get(self.TOKEN_URL, params=params, timeout=10)
        data = resp.json()
        if 'access_token' not in data:
            raise WeChatAPIError(data)
        return data['access_token']

    def get_qr_ticket(self, scene_str, expire_seconds=300):
        """生成公众号临时二维码 ticket（返回微信二维码内容字符串）。"""
        token = self.get_access_token()
        body = {
            'expire_seconds': expire_seconds,
            'action_name': 'QR_STR_SCENE',
            'action_info': {'scene': {'scene_str': scene_str}},
        }
        resp = requests.post(
            f'{self.QRCODE_URL}?access_token={token}', json=body, timeout=10
        )
        data = resp.json()
        if 'ticket' not in data:
            raise WeChatAPIError(data)
        return data['ticket']


def get_wechat_service(app=None):
    """从 Flask 配置构建 WeChatService（自动应用 mock 开关）。"""
    app = app or current_app
    return WeChatService(
        app_id=app.config.get('WECHAT_APP_ID', ''),
        app_secret=app.config.get('WECHAT_APP_SECRET', ''),
        mock=app.config.get('WECHAT_MOCK', False),
    )
