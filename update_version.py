"""
自动更新版本号脚本
每次 Git commit 时自动递增版本号
- 支持两位版本号格式（如 2.1, 2.2, 3.0）
- 同步更新 FileVersion 和 ProductVersion
- 根据 commit 信息智能升级版本号
"""
import re
import sys
import os


def get_commit_message():
    """获取 Git commit 消息"""
    # 从 Git commit 消息文件读取
    commit_msg_file = '.git/COMMIT_EDITMSG'
    if os.path.exists(commit_msg_file):
        try:
            with open(commit_msg_file, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except:
            pass
    return ""


def should_bump_major(commit_msg):
    """
    判断是否应该升级主版本号
    规则：commit 信息包含"实现"且包含"功能"时，升级主版本
    """
    if not commit_msg:
        return False
    
    # 检查是否包含关键词
    keywords_patterns = [
        r'实现.*功能',  # "实现XX功能"
        r'功能.*实现',  # "功能XX实现"
        r'新增.*功能',  # "新增XX功能"
        r'添加.*功能',  # "添加XX功能"
    ]
    
    for pattern in keywords_patterns:
        if re.search(pattern, commit_msg, re.IGNORECASE):
            return True
    
    return False


def increment_version(version_str, is_major=False):
    """
    递增版本号（两位格式）
    例如：
    - 次版本：2.1 -> 2.2
    - 主版本：2.1 -> 3.0
    """
    parts = [int(x) for x in version_str.split('.')]
    
    # 确保至少有两位
    while len(parts) < 2:
        parts.append(0)
    
    if is_major:
        # 升级主版本，次版本归零
        parts[0] += 1
        parts[1] = 0
    else:
        # 升级次版本
        parts[1] += 1
    
    return f"{parts[0]}.{parts[1]}"


def version_to_tuple(version_str):
    """
    将两位版本号转换为四位元组（用于 filevers/prodvers）
    例如：2.1 -> (2, 1, 0, 0)
    """
    parts = [int(x) for x in version_str.split('.')]
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])


def update_version_file(commit_msg=""):
    """更新 version_info.txt 文件中的版本号"""
    file_path = 'version_info.txt'
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取当前的 FileVersion
        file_version_match = re.search(r"StringStruct\(u'FileVersion', u'([\d.]+)'\)", content)
        if not file_version_match:
            print("✗ 未找到 FileVersion")
            return False
        
        current_version = file_version_match.group(1)
        
        # 判断是否升级主版本
        is_major = should_bump_major(commit_msg)
        new_version = increment_version(current_version, is_major)
        
        # 更新 FileVersion（保持两位格式）
        content = re.sub(
            r"(StringStruct\(u'FileVersion', u')([\d.]+)('\))",
            rf"\g<1>{new_version}\3",
            content
        )
        
        # 更新 ProductVersion（保持两位格式）
        content = re.sub(
            r"(StringStruct\(u'ProductVersion', u')([\d.]+)('\))",
            rf"\g<1>{new_version}\3",
            content
        )
        
        # 更新 filevers 元组
        version_tuple = version_to_tuple(new_version)
        content = re.sub(
            r"(filevers=\()\d+,\s*\d+,\s*\d+,\s*\d+(\))",
            rf"\g<1>{version_tuple[0]}, {version_tuple[1]}, {version_tuple[2]}, {version_tuple[3]}\2",
            content
        )
        
        # 更新 prodvers 元组
        content = re.sub(
            r"(prodvers=\()\d+,\s*\d+,\s*\d+,\s*\d+(\))",
            rf"\g<1>{version_tuple[0]}, {version_tuple[1]}, {version_tuple[2]}, {version_tuple[3]}\2",
            content
        )
        
        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        version_type = "主版本" if is_major else "次版本"
        print(f"✓ 版本号已更新 ({version_type}): {current_version} -> {new_version}")
        if is_major and commit_msg:
            print(f"  检测到功能实现关键词，升级主版本")
        
        return True
            
    except Exception as e:
        print(f"✗ 更新版本失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    # 如果提供了 commit 消息参数，使用它
    commit_msg = sys.argv[1] if len(sys.argv) > 1 else get_commit_message()
    update_version_file(commit_msg)
