from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging
import os
from datetime import datetime
from dotenv import load_dotenv
import requests # 导入 requests 库，用于 HTTP 请求
import re # 导入 re 模块，用于正则表达式

# 加载 .env 文件中的环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('signin.log'),
        logging.StreamHandler()
    ]
)

# 您的 Server酱 发送函数
def sc_send(sendkey, title, desp='', options=None):
    if options is None:
        options = {}
    # 判断 sendkey 是否以 'sctp' 开头，并提取数字构造 URL
    if sendkey.startswith('sctp'):
        match = re.match(r'sctp(\d+)t', sendkey)
        if match:
            num = match.group(1)
            url = f'https://{num}.push.ft07.com/send/{sendkey}.send'
        else:
            raise ValueError('Invalid sendkey format for sctp')
    else:
        url = f'https://sctapi.ftqq.com/{sendkey}.send'
    params = {
        'title': title,
        'desp': desp,
        **options
    }
    # Server酱新版推荐使用 application/json;charset=utf-8
    headers = {
        'Content-Type': 'application/json;charset=utf-8' 
    }
    try:
        response = requests.post(url, json=params, headers=headers)
        response.raise_for_status() # 对 4xx 或 5xx 响应引发 HTTPError
        result = response.json()
        return result
    except requests.exceptions.RequestException as e:
        logging.error(f"发送 Server酱通知时发生网络错误: {e}")
        return {"code": -1, "message": f"网络错误: {e}"}
    except Exception as e:
        logging.error(f"发送 Server酱通知时发生未知错误: {e}")
        return {"code": -1, "message": f"未知错误: {e}"}


class AutoSignIn:
    def __init__(self, username, password, sendkey=None):
        self.username = username
        self.password = password
        self.sendkey = sendkey # 将 sendkey 传递给构造函数
        self.driver = None
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # 创建 screenshots 目录（如果不存在）
        self.screenshot_dir = os.path.join(script_dir, "screenshots")
        if not os.path.exists(self.screenshot_dir):
            os.makedirs(self.screenshot_dir)

    def setup_driver(self):
        """设置浏览器驱动"""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # 无头模式
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-extensions')
        # 确保 /usr/bin/google-chrome 是您的 Chrome 浏览器可执行文件的正确路径
        options.binary_location = '/usr/bin/google-chrome' 
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        logging.info("浏览器驱动初始化完成")

    def take_screenshot(self, name):
        """保存截图"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.screenshot_dir}/{name}_{timestamp}.png"
        self.driver.save_screenshot(filename)
        logging.info(f"截图已保存: {filename}")
        return filename

    def send_signin_notification(self, title, content):
        """
        通过 Server酱 发送通知 (封装您的 sc_send 函数)
        :param title: 通知标题
        :param content: 通知内容
        """
        if not self.sendkey:
            logging.warning("未设置 Server酱 SENDKEY，跳过通知发送。")
            return

        logging.info(f"正在发送 Server酱 通知，标题: {title}, 内容: {content}")
        result = sc_send(self.sendkey, title, desp=content)
        if result.get('code') == 0:
            logging.info(f"Server酱通知发送成功: {title}")
        else:
            logging.error(f"Server酱通知发送失败: {result.get('message', '未知错误')}")


    def login(self):
        """登录网站"""
        try:
            self.driver.get("https://vip.taoqitu.pro/index.html")
            logging.info("访问登录页面")

            # 等待登录表单加载
            username_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "regusername"))
            )
            password_box = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "regpassword"))
            )

            # 输入账号密码
            username_box.send_keys(self.username)
            password_box.send_keys(self.password)
            
            # 点击登录按钮
            login_button = self.driver.find_element(By.CLASS_NAME, "loginbutton")
            login_button.click()
            
            logging.info("登录成功")
            time.sleep(5)  # 等待登录完成
            
        except Exception as e:
            logging.error(f"登录失败: {str(e)}")
            self.take_screenshot("login_error")  # 登录失败时截图
            self.send_signin_notification("自动签到通知", f"登录失败: {str(e)}")
            raise

    def sign_in(self):
        """执行签到操作"""
        try:
            self.driver.get("https://vip.taoqitu.pro/qiandao.html")
            logging.info("访问签到页面")
            
            time.sleep(5)

            # 签到页面截图
            self.take_screenshot("before_signin")

            # 等待签到按钮加载
            sign_button = self.driver.find_element(By.CLASS_NAME, "invite_get_amount")
            
            # 点击签到按钮
            sign_button.click()
            logging.info("签到操作执行完成")
            
            # 等待签到结果显示
            time.sleep(5)
            
            # 签到后截图
            screenshot_path = self.take_screenshot("after_signin")
            logging.info(f"签到结果已截图保存: {screenshot_path}")
            
        except Exception as e:
            logging.error(f"签到失败: {str(e)}")
            self.take_screenshot("signin_error")  # 签到失败时截图
            self.send_signin_notification("自动签到通知", f"签到失败: {str(e)}")
            raise

    def run(self):
        """运行完整的签到流程"""
        try:
            self.setup_driver()
            self.login()
            self.sign_in()
            logging.info("自动签到流程完成")
            self.send_signin_notification("自动签到通知", "自动签到流程全部完成！")
        except Exception as e:
            logging.error(f"自动签到过程出错: {str(e)}")
            self.send_signin_notification("自动签到通知", f"自动签到流程中发生错误: {str(e)}")
        finally:
            if self.driver:
                self.driver.quit()
                logging.info("浏览器驱动已关闭")

if __name__ == "__main__":
    # 从环境变量获取账号密码
    USERNAME = os.getenv("SIGNIN_USERNAME")
    PASSWORD = os.getenv("SIGNIN_PASSWORD")
    # 修改为读取 SENDKEY
    SENDKEY = os.getenv("SENDKEY") 

    if not USERNAME or not PASSWORD:
        logging.error("请设置环境变量 SIGNIN_USERNAME 和 SIGNIN_PASSWORD")
        exit(1)
    
    # 将 SENDKEY 传递给 AutoSignIn 构造函数
    auto_signin = AutoSignIn(USERNAME, PASSWORD, SENDKEY)
    auto_signin.run()
