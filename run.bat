@echo off
title War Era - Jet Market Analyzer
echo 🔍 جاري تشغيل محلل سوق الطائرات...
echo ====================================
cd /d C:\Users\3BBADI\Desktop\New folder\war_era_analyzer-Manus-Test
python -m streamlit run app.py --server.headless true
pause