# OCR部署指南

## 服务器端Tesseract安装

### Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-chi-sim tesseract-ocr-eng
```

### CentOS/RHEL:
```bash
sudo yum install epel-release
sudo yum install tesseract
sudo yum install tesseract-langpack-chi_sim tesseract-langpack-eng
```

### macOS (开发环境):
```bash
brew install tesseract
brew install tesseract-lang
```

## Render.com部署配置

在Render.com上需要添加build script:

### render.yaml (如果使用):
```yaml
services:
  - type: web
    name: shh-elf
    env: python
    buildCommand: |
      apt-get update
      apt-get install -y tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng
      pip install -r requirements.txt
    startCommand: python main.py
```

### 或者在Web Service设置中添加Build Command:
```bash
apt-get update && apt-get install -y tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng && pip install -r requirements.txt
```

## 测试OCR功能

部署后测试OCR是否正常工作:

```bash
# 在服务器上测试
tesseract --version
tesseract --list-langs
```

应该显示包含 `chi_sim` 和 `eng` 语言包。

## 本地测试

```python
import pytesseract
print(pytesseract.get_tesseract_version())
print(pytesseract.get_languages())
```

## OCR优化策略

1. **图像预处理**: 灰度化 → 对比度增强 → 降噪 → 锐化
2. **语言支持**: 中文简体 + 英文混合识别
3. **字符白名单**: 限制识别字符范围提高准确率
4. **多重回退**: OCR失败时仍可使用纯视觉分析

## 性能考虑

- OCR处理增加约2-3秒分析时间
- 但大大提升书名识别准确率
- 服务器内存使用增加约50MB