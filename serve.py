import logging
import random
import time

import c104

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IEC104Server:
    def __init__(self, host="0.0.0.0", port=2404):
        self.host = host
        self.port = port
        
        # 创建服务器实例
        self.server = c104.Server(ip=self.host, port=self.port)
        
        # 添加站点(RTU/子站)
        self.station = self.server.add_station(common_address=47)
        
        # 初始化数据点
        self.points = {}
        self._init_points()
        
        # 控制值状态
        self.control_status = False
        self.setpoint_value = 0.0

    def _init_points(self):
        """初始化数据点"""
        # 添加测量值点
        self.points['temp'] = self.station.add_point(
            io_address=11,
            type=c104.Type.M_ME_NC_1,
            report_ms=1000
        )
        
        self.points['pressure'] = self.station.add_point(
            io_address=12,
            type=c104.Type.M_ME_NC_1,
            report_ms=1000
        )
        
        # 添加状态点
        self.points['status'] = self.station.add_point(
            io_address=21,
            type=c104.Type.M_SP_NA_1,
            report_ms=1000
        )
        
        # 添加控制点
        self.points['control'] = self.station.add_point(
            io_address=31,
            type=c104.Type.C_SC_NA_1
        )
        
        # 添加设点命令点
        self.points['setpoint'] = self.station.add_point(
            io_address=32,
            type=c104.Type.C_SE_NC_1
        )

    def update_data(self):
        """更新测量值（模拟数据）"""
        try:
            # 检查控制点和设点的值
            self._check_control_values()
            
            # 更新温度值
            if self.control_status:  # 如果控制开关打开，使用设定值
                target_temp = self.setpoint_value
                current_temp = self.points['temp'].value or 25.0
                # 温度缓慢接近目标值
                if abs(current_temp - target_temp) > 0.1:
                    new_temp = current_temp + (target_temp - current_temp) * 0.1
                else:
                    new_temp = target_temp
                new_temp += random.uniform(-0.1, 0.1)  # 小幅波动
            else:  # 控制开关关闭，使用默认模拟值
                new_temp = 25.0 + random.uniform(-1.0, 1.0)
            
            self.points['temp'].value = new_temp
            # logger.info(f"Temperature updated: {new_temp:.2f}°C (Control: {self.control_status}, "
            #            f"Setpoint: {self.setpoint_value:.1f})")
            
            # 更新压力值
            pressure = 100.0 + random.uniform(-5.0, 5.0)
            self.points['pressure'].value = pressure
            # logger.info(f"Pressure updated: {pressure:.2f}kPa")
            
            # 更新状态值
            status = random.choice([True, False])
            self.points['status'].value = status
            # logger.info(f"Status updated: {status}")
            
        except Exception as e:
            logger.error(f"Error updating data: {e}")

    def _check_control_values(self):
        """检查和更新控制值"""
        try:
            # 检查控制点的值是否改变
            control_value = self.points['control'].value
            logger.info(f"Control status changed to: {control_value}")
            
            # 检查设点值是否改变
            setpoint_value = self.points['setpoint'].value
            logger.info(f"Setpoint value changed to: {setpoint_value}")
                
        except Exception as e:
            logger.error(f"Error checking control values: {e}")

    def start(self):
        """启动服务器"""
        try:
            logger.info(f"Starting IEC104 server on {self.host}:{self.port}")
            self.server.start()
            logger.info("Server started successfully")
            
            while True:
                self.update_data()
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received stop signal")
            self.stop()
        except Exception as e:
            logger.error(f"Server error: {e}")
            self.stop()

    def stop(self):
        """停止服务器"""
        try:
            self.server.stop()
            logger.info("Server stopped")
        except Exception as e:
            logger.error(f"Error stopping server: {e}")

def main():
    server = IEC104Server()
    server.start()

if __name__ == "__main__":
    main()