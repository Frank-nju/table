#!/usr/bin/env python3
"""
自动提取人名并填充用户档案

从活动和报名数据中提取所有唯一的人名，为每个人创建用户档案
"""

from models.database import db
from config import (
    ACTIVITY_TABLE_NAME,
    SIGNUP_TABLE_NAME,
    USER_PROFILE_TABLE_NAME,
    ACTIVITY_COL_SPEAKERS,
    SIGNUP_COL_NAME,
    USER_COL_NAME,
    USER_COL_EMAIL,
    USER_COL_ROLE,
    USER_COL_FIRST_SEEN_AT
)
import datetime

def extract_names():
    """提取所有唯一的人名"""
    # 存储所有唯一的名字
    unique_names = set()
    
    # 从活动中提取分享者
    activities = db.list_rows(ACTIVITY_TABLE_NAME)
    for activity in activities:
        speakers = activity.get(ACTIVITY_COL_SPEAKERS, "")
        if speakers:
            # 处理可能的逗号分隔的多个名字
            for speaker in speakers.split(","):
                speaker = speaker.strip()
                if speaker:
                    unique_names.add(speaker)
    
    # 从报名中提取姓名
    signups = db.list_rows(SIGNUP_TABLE_NAME)
    for signup in signups:
        name = signup.get(SIGNUP_COL_NAME, "")
        if name:
            unique_names.add(name)
    
    return unique_names

def create_user_profiles(names):
    """为每个名字创建用户档案"""
    # 获取现有的用户档案
    existing_profiles = db.list_rows(USER_PROFILE_TABLE_NAME)
    existing_names = {profile.get(USER_COL_NAME, "") for profile in existing_profiles}
    
    # 为新名字创建用户档案
    created_count = 0
    for name in names:
        if name and name not in existing_names:
            # 创建新用户档案
            profile_data = {
                USER_COL_NAME: name,
                USER_COL_EMAIL: "",  # 默认为空
                USER_COL_ROLE: "",  # 默认为空
                USER_COL_FIRST_SEEN_AT: datetime.datetime.now().isoformat()
            }
            db.append_row(USER_PROFILE_TABLE_NAME, profile_data)
            created_count += 1
            print(f"Created user profile for: {name}")
    
    return created_count

def main():
    """主函数"""
    print("Extracting names...")
    unique_names = extract_names()
    print(f"Found {len(unique_names)} unique names")
    
    print("Creating user profiles...")
    created_count = create_user_profiles(unique_names)
    print(f"Created {created_count} new user profiles")
    
    # 验证结果
    total_profiles = len(db.list_rows(USER_PROFILE_TABLE_NAME))
    print(f"Total user profiles now: {total_profiles}")

if __name__ == "__main__":
    main()
