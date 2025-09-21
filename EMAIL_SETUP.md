# 📧 邮箱验证系统配置指南

## 🎯 **只需要一个发送邮箱**

你只需要设置**一个邮箱**用来发送验证邮件，用户可以用**任何邮箱**注册。

## 🔧 **Render环境变量配置**

在Render Dashboard中设置以下环境变量：

### 必须设置：
```bash
EMAIL_USER=your-email@example.com     # 你的发送邮箱
EMAIL_PASSWORD=your-app-password      # 邮箱应用密码
SECRET_KEY=kD6x6RYSstiag52JT18kiEFHjj8yx-fo49UVBn19Yxg
```

### 可选设置（系统会自动检测）：
```bash
SMTP_SERVER=smtp.gmail.com           # 自动检测，可不设置
SMTP_PORT=587                        # 自动检测，可不设置
```

## 📮 **支持的邮箱服务商**

系统自动支持以下邮箱作为发送邮箱：

### 🌟 **推荐使用**
- **Gmail** (gmail.com) - 最稳定
- **QQ邮箱** (qq.com) - 国内用户友好

### 📧 **完整支持列表**
- Gmail: gmail.com
- QQ邮箱: qq.com, vip.qq.com
- 网易邮箱: 163.com, 126.com
- Outlook: outlook.com, hotmail.com, live.com
- 新浪邮箱: sina.com
- 搜狐邮箱: sohu.com
- 阿里云邮箱: aliyun.com

## 🔑 **各邮箱服务商设置方法**

### Gmail设置
1. 开启两步验证
2. 生成应用密码：Google账户 → 安全性 → 应用密码
3. 设置环境变量：
   ```
   EMAIL_USER=yourname@gmail.com
   EMAIL_PASSWORD=生成的16位应用密码
   ```

### QQ邮箱设置
1. 登录QQ邮箱 → 设置 → 账户
2. 开启SMTP服务
3. 获取授权码
4. 设置环境变量：
   ```
   EMAIL_USER=yourname@qq.com
   EMAIL_PASSWORD=获取的授权码
   ```

### 163邮箱设置
1. 登录163邮箱 → 设置 → POP3/SMTP/IMAP
2. 开启SMTP服务
3. 获取授权密码
4. 设置环境变量：
   ```
   EMAIL_USER=yourname@163.com
   EMAIL_PASSWORD=获取的授权密码
   ```

## ⚠️ **重要提醒**

1. **不要用个人常用邮箱**：建议创建专门的服务邮箱
2. **使用应用密码**：不要使用邮箱登录密码
3. **保护密码安全**：不要将密码提交到代码仓库

## 🚀 **如果暂时不配置邮箱**

- 不设置 `EMAIL_USER` 和 `EMAIL_PASSWORD`
- 系统会自动跳过邮箱验证
- 用户注册后直接可以使用

## 📝 **设置示例**

假设你选择用Gmail：

1. 创建专用Gmail账户：`shhelf.noreply@gmail.com`
2. 开启两步验证
3. 生成应用密码：`abcd efgh ijkl mnop`
4. 在Render设置：
   ```
   EMAIL_USER=shhelf.noreply@gmail.com
   EMAIL_PASSWORD=abcdefghijklmnop
   ```

用户可以用任何邮箱注册：
- user1@gmail.com ✓
- user2@qq.com ✓
- user3@163.com ✓
- user4@outlook.com ✓

都会收到来自 `shhelf.noreply@gmail.com` 的验证邮件！