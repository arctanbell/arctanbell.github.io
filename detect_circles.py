#!/usr/bin/env python3
"""
圆形检测程序
使用OpenCV的Hough Circle Transform算法检测图像中的圆形

用法:
    python detect_circles.py <input_image_path> [output_image_path]
    
参数:
    input_image_path  : 输入图像路径（必需）
    output_image_path : 输出图像路径（可选，默认为'output_with_circles.jpg'）

依赖:
    pip install opencv-python numpy
"""

import cv2
import numpy as np
import sys
import os

def detect_circles(image_path, output_path=None):
    """
    检测图像中的圆形
    
    参数:
        image_path: 输入图像路径
        output_path: 输出图像路径（可选）
    
    返回:
        circles: 检测到的圆形列表 [[x, y, radius], ...]
    """
    # 读取图像
    image = cv2.imread(image_path)
    if image is None:
        print(f"错误: 无法读取图像 {image_path}")
        return None
    
    # 创建输出路径
    if output_path is None:
        output_path = "output_with_circles.jpg"
    
    # 保存原始图像用于显示
    original = image.copy()
    
    # 转换为灰度图
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 应用高斯模糊减少噪声
    blurred = cv2.GaussianBlur(gray, (9, 9), 2)
    
    # 使用Hough Circle Transform检测圆形
    # 参数说明:
    # dp=1: 累加器分辨率与输入图像分辨率的反比
    # minDist=50: 检测到的圆心之间的最小距离
    # param1=50: Canny边缘检测的高阈值
    # param2=30: 累加器阈值，越小检测到的圆形越多（但可能包含假阳性）
    # minRadius=10: 最小圆半径
    # maxRadius=100: 最大圆半径
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1,
        minDist=50,
        param1=50,
        param2=30,
        minRadius=10,
        maxRadius=100
    )
    
    # 如果检测到圆形
    if circles is not None:
        # 将坐标和半径转换为整数
        circles = np.round(circles[0, :]).astype("int")
        
        print(f"检测到 {len(circles)} 个圆形:")
        for i, (x, y, r) in enumerate(circles):
            print(f"  圆 {i+1}: 中心({x}, {y}), 半径 {r}")
            
            # 在原图上绘制圆形
            cv2.circle(original, (x, y), r, (0, 255, 0), 2)  # 绿色圆圈
            cv2.circle(original, (x, y), 2, (0, 0, 255), 3)   # 红色圆心
        
        # 保存结果图像
        cv2.imwrite(output_path, original)
        print(f"结果已保存到: {output_path}")
        
    else:
        print("未检测到任何圆形")
        # 保存原始图像
        cv2.imwrite(output_path, original)
        print(f"原始图像已保存到: {output_path}")
    
    return circles

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python detect_circles.py <input_image_path> [output_image_path]")
        print("示例: python detect_circles.py input.jpg output.jpg")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    # 检查输入文件是否存在
    if not os.path.exists(input_path):
        print(f"错误: 输入文件 {input_path} 不存在")
        sys.exit(1)
    
    # 执行圆形检测
    circles = detect_circles(input_path, output_path)
    
    if circles is not None:
        print("\n检测完成！")
        if circles is not None and len(circles) > 0:
            print("查看输出图像以看到标记的圆形。")
        else:
            print("尝试调整参数或检查图像中是否有明显的圆形。")

if __name__ == "__main__":
    main()