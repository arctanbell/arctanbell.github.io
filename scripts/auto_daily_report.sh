#!/bin/bash
# 自动每日市场报告脚本
cd /home/admin/clawd
source /home/admin/.bashrc 2>/dev/null || true

# 运行Python脚本生成报告
python3 scripts/daily_market_report.py

# 检查报告是否生成成功
if [ -f "memory/daily_reports/latest_report.txt" ]; then
    echo "✅ 每日市场报告已成功生成！"
    cat memory/daily_reports/latest_report.txt
else
    echo "❌ 报告生成失败，请检查脚本"
fi