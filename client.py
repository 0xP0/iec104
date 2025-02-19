import logging
import random
import time
from datetime import datetime
import os
import c104

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IEC104Client:
    def __init__(self):
        # 创建客户端实例
        self.client = c104.Client(
            tick_rate_ms=1000,  # 增加tick rate以确保更稳定的帧同步
            command_timeout_ms=5000
        )
        
        # 添加连接
        self.connection = self.client.add_connection(
            ip="192.168.71.87",
            port=2404,
            init=c104.Init.NONE  # 修改为手动控制初始化过程
        )
        
        # 添加站点
        self.station = self.connection.add_station(common_address=1)
        
        # 初始化数据点字典
        self.single_points = {}     # 单点数据 (1-2)
        self.double_points = {}     # 双点数据 (200-203)
        self.normalized_points = {} # 归一化值 (1793-1800)
        
        # 链路测试相关
        self.last_frame_time = time.time()  # 最后一次接收帧的时间
        self.t3_timeout = 20  # t3超时时间（秒）
        self.test_point = None  # 测试点
        
        # 初始化数据点
        self._init_points()
        
        # 初始化测试点
        self._init_test_point()

    def _init_points(self):
        """初始化数据点"""
        # 添加单点数据 (1-2)
        for i in range(1, 3):  # 2个单点数据
            point_name = f"SPI_{i}"
            self.single_points[point_name] = self.station.add_point(
                io_address=i,
                type=c104.Type.M_SP_NA_1,  # 单点信息
                report_ms=0,  # 0表示不进行周期上报
                command_mode=c104.CommandMode.DIRECT
            )
        
        # 添加双点数据 (200-203)
        for i in range(200, 204):  # 4个双点数据
            point_name = f"DPI_{i}"
            self.double_points[point_name] = self.station.add_point(
                io_address=i,
                type=c104.Type.M_DP_NA_1,  # 双点信息
                report_ms=0,
                command_mode=c104.CommandMode.DIRECT
            )
        
        # 添加归一化值 (1793-1800)
        for i in range(1793, 1801):  # 8个归一化值
            point_name = f"NVA_{i}"
            self.normalized_points[point_name] = self.station.add_point(
                io_address=i,
                type=c104.Type.M_ME_NA_1,  # 归一化值
                report_ms=0,
                command_mode=c104.CommandMode.DIRECT
            )
        
        # 添加总召唤点
        self.interrogation_point = self.station.add_point(
            io_address=0,
            type=c104.Type.C_SC_NA_1,  # 单命令
            command_mode=c104.CommandMode.DIRECT
        )

    def _init_test_point(self):
        """初始化测试点"""
        try:
            # 创建测试点，使用特殊地址0
            self.test_point = self.station.add_point(
                io_address=0,
                type=c104.Type.C_SC_NA_1,  # 使用单命令类型
                command_mode=c104.CommandMode.DIRECT
            )
            logger.info("Test point initialized")
        except Exception as e:
            logger.error(f"Error initializing test point: {e}")

    def _on_connect(self):
        """连接建立回调"""
        logger.info("Connection established")
        # 连接建立后执行时钟同步
        self.sync_clock()
        # 执行总召唤
        self.general_interrogation()

    def _on_disconnect(self):
        """连接断开回调"""
        logger.info("Connection lost")

    def general_interrogation(self):
        """执行总召唤"""
        try:
            logger.info("Initiating general interrogation")
            # 发送总召唤命令
            self.interrogation_point.value = True  # 激活总召唤
            logger.info("General interrogation command sent")
        except Exception as e:
            logger.error(f"Error during general interrogation: {e}")

    def group_interrogation(self, group):
        """执行群组召唤
        Args:
            group: 群组号(1-16)，对应INRO1-INRO16
        """
        if not 1 <= group <= 16:
            logger.error("Invalid group number. Must be between 1 and 16")
            return
        
        try:
            logger.info(f"Initiating group {group} interrogation")
            # 创建群组召唤点
            interrogation_point = self.station.add_point(
                io_address=group,  # 使用群组号作为地址
                type=c104.Type.C_SC_NA_1,  # 单命令
                command_mode=c104.CommandMode.DIRECT
            )
            # 发送群组召唤命令
            interrogation_point.value = True
        except Exception as e:
            logger.error(f"Error during group interrogation: {e}")

    def sync_clock(self):
        """执行时钟同步"""
        try:
            current_time = datetime.now()
            logger.info(f"Synchronizing clock to {current_time}")
            # 创建时钟同步点
            clock_point = self.station.add_point(
                io_address=0,  # 使用0作为时钟同步的地址
                type=c104.Type.C_SC_NA_1,  # 单命令
                command_mode=c104.CommandMode.DIRECT
            )
            # 发送时钟同步命令
            clock_point.value = True
        except Exception as e:
            logger.error(f"Error during clock synchronization: {e}")

    def send_test_frame(self):
        """发送测试帧"""
        try:
            if self.test_point:
                logger.info("Sending test frame (TESTFR act)")
                # 发送测试激活帧
                self.test_point.value = True
                self.last_frame_time = time.time()  # 更新最后发送时间
                logger.info("Test frame sent")
        except Exception as e:
            logger.error(f"Error sending test frame: {e}")

    def check_link_status(self):
        """检查链路状态，必要时发送测试帧"""
        current_time = time.time()
        if current_time - self.last_frame_time > self.t3_timeout:
            logger.info(f"Link timeout ({self.t3_timeout}s), sending test frame")
            self.send_test_frame()

    def start(self):
        """启动客户端"""
        try:
            logger.info(f"Starting IEC104 client, connecting to 192.168.71.87:2404")
            self.client.start()
            logger.info("Client started successfully")
            
            # 等待连接建立
            time.sleep(2)  # 增加等待时间确保连接完全建立
            
            # 先执行时钟同步
            self.sync_clock()
            time.sleep(1)  # 等待时钟同步完成
            
            # 然后执行总召唤
            self.general_interrogation()
            
        except Exception as e:
            logger.error(f"Error starting client: {e}")
            raise

    def stop(self):
        """停止客户端"""
        try:
            self.client.stop()
            logger.info("Client stopped")
        except Exception as e:
            logger.error(f"Error stopping client: {e}")

    def get_monitor_value(self, point_name):
        """获取监视点的值"""
        if point_name in self.single_points:
            return self.single_points[point_name].value
        elif point_name in self.double_points:
            return self.double_points[point_name].value
        elif point_name in self.normalized_points:
            return self.normalized_points[point_name].value
        return None

    def send_command(self, point_name, value):
        """发送控制命令"""
        print(f"Sending command to {point_name}: {value}")
        try:
            if point_name in self.single_points:
                point = self.single_points[point_name]
                
                # 对于设点命令，先确保值是浮点数
                if point.type == c104.Type.C_SE_NC_1:
                    value = float(value)
                    # logger.info(f"Sending setpoint command to {point_name}: {value}")
                
                # 使用属性直接设置值
                point.value = value
                
                # 添加确认日志
                # logger.info(f"Command sent to {point_name}: {value} (type: {type(value)})")
                
                # 添加验证
                time.sleep(0.5)  # 等待一点时间让值更新
                current_value = point.value
                logger.info(f"Verification - {point_name} current value: {current_value}")
            elif point_name in self.double_points:
                point = self.double_points[point_name]
                
                # 对于双点命令，先确保值是浮点数
                if point.type == c104.Type.C_SE_NC_1:
                    value = float(value)
                    # logger.info(f"Sending setpoint command to {point_name}: {value}")
                
                # 使用属性直接设置值
                point.value = value
                
                # 添加确认日志
                # logger.info(f"Command sent to {point_name}: {value} (type: {type(value)})")
                
                # 添加验证
                time.sleep(0.5)  # 等待一点时间让值更新
                current_value = point.value
                logger.info(f"Verification - {point_name} current value: {current_value}")
            elif point_name in self.normalized_points:
                point = self.normalized_points[point_name]
                
                # 对于归一化值命令，先确保值是浮点数
                if point.type == c104.Type.C_SE_NC_1:
                    value = float(value)
                    # logger.info(f"Sending setpoint command to {point_name}: {value}")
                
                # 使用属性直接设置值
                point.value = value
                
                # 添加确认日志
                # logger.info(f"Command sent to {point_name}: {value} (type: {type(value)})")
                
                # 添加验证
                time.sleep(0.5)  # 等待一点时间让值更新
                current_value = point.value
                logger.info(f"Verification - {point_name} current value: {current_value}")
            else:
                logger.error(f"Control point {point_name} not found")
        except Exception as e:
            logger.error(f"Error sending command: {e}")


def main():
    client = IEC104Client()
    
    try:
        # 启动客户端
        client.start()
        
        # 主循环
        while True:
            try:
                # 检查链路状态
                client.check_link_status()
                
                # 清空终端
                os.system('cls' if os.name == 'nt' else 'clear')
                # 示例：读取一些数据点的值
                # 读取单点数据示例
                for point_name, point in client.single_points.items():
                    if point.value is not None:
                        logger.info(f"{point_name}: {point.value}")
                # 读取双点数据示例
                for point_name, point in client.double_points.items():
                    if point.value is not None:
                        logger.info(f"{point_name}: {point.value}")
                
                # 读取归一化值示例
                for point_name, point in client.normalized_points.items():
                    if point.value is not None:
                        logger.info(f"{point_name}: {point.value}")
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Received stop signal")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(5)
    
    finally:
        client.stop()

if __name__ == "__main__":
    main()