#!/usr/bin/env python3

import os
import sys
import json
import requests
import logging
from datetime import datetime, timedelta, timezone

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SIGN_URL    = "https://sg-hk4e-api.hoyolab.com/event/sol/sign"
INFO_URL    = "https://sg-hk4e-api.hoyolab.com/event/sol/info"
REWARD_URL  = "https://sg-hk4e-api.hoyolab.com/event/sol/home"
GAME_URL    = "https://sg-hk4e-api.hoyoverse.com/game_record/genshin/api/dailyNote"
ACT_ID      = "e202102251931481"
UTC8        = timezone(timedelta(hours=8))


def get_headers(cookie, user_agent):
    safe_cookie = cookie.encode("utf-8").decode("latin-1", errors="ignore")
    return {
        "Cookie": safe_cookie,
        "User-Agent": user_agent,
        "Referer": "https://act.hoyolab.com/",
        "Origin": "https://act.hoyolab.com/",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "application/json, text/plain, */*",
    }


def get_sign_info(cookie, user_agent):
    headers = get_headers(cookie, user_agent)
    res = requests.get(f"{INFO_URL}?act_id={ACT_ID}", headers=headers, timeout=10)
    data = res.json()
    logger.info(f"Sign info: {data.get('retcode')}")
    if data.get("retcode") == 0:
        return data["data"]
    return None


def get_reward_list(cookie, user_agent):
    headers = get_headers(cookie, user_agent)
    res = requests.get(f"{REWARD_URL}?act_id={ACT_ID}", headers=headers, timeout=10)
    data = res.json()
    if data.get("retcode") == 0:
        return data["data"].get("awards", [])
    return []


def get_resin_info(uid, server, cookie, user_agent):
    headers = get_headers(cookie, user_agent)
    
    server_map = {
        "os_asia": "os_asia",
        "os_cht": "os_cht",
        "os_euro": "os_euro",
        "os_usa": "os_usa"
    }
    
    game_server = server_map.get(server, "os_asia")
    
    params = {
        "uid": uid,
        "server": game_server
    }
    try:
        logger.info(f"Fetching resin data for UID: {uid}, Server: {game_server}")
        logger.info(f"Resin API URL: {GAME_URL}")
        logger.info(f"Resin API params: {params}")
        
        res = requests.get(GAME_URL, params=params, headers=headers, timeout=10)
        logger.info(f"Resin API status code: {res.status_code}")
        logger.info(f"Resin API full response: {res.text}")
        
        if res.status_code != 200:
            logger.error(f"Resin API HTTP error: {res.status_code}")
            return None
            
        data = res.json()
        retcode = data.get("retcode", -1)
        message = data.get("message", "")
        logger.info(f"Resin retcode: {retcode}, message: {message}")
        
        if retcode == 0:
            logger.info(f"Resin data retrieved successfully")
            return data["data"]
        else:
            logger.warning(f"Resin API error retcode {retcode}: {message}")
            return None
    except Exception as e:
        logger.error(f"Resin API exception: {type(e).__name__}: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    return None


def do_sign(cookie, user_agent):
    headers = get_headers(cookie, user_agent)
    res = requests.post(f"{SIGN_URL}?act_id={ACT_ID}", headers=headers, timeout=10)
    data = res.json()
    logger.info(f"Sign response: {data.get('retcode')}")
    return data


def calculate_resin_recovery_time(current_resin, max_resin=160):
    if current_resin >= max_resin:
        return None
    
    resin_needed = max_resin - current_resin
    minutes_needed = resin_needed * 8
    
    now = datetime.now(UTC8)
    recovery_time = now + timedelta(minutes=minutes_needed)
    
    return recovery_time


def is_cookie_expiring_soon():
    now = datetime.now(UTC8)
    return now.day >= 25


def summarize_monthly_rewards(rewards, total_sign_days):
    summary = {}
    for reward in rewards[:total_sign_days]:
        name = reward.get("name", "Unknown")
        cnt  = reward.get("cnt", 0)
        summary[name] = summary.get(name, 0) + cnt
    return summary


def build_report(user_name, sign_info, rewards, today_reward, tomorrow_reward, already_signed):
    now  = datetime.now(UTC8)
    tmrw = now + timedelta(days=1)

    total_sign_days = sign_info.get("total_sign_day", 0)
    missed_days     = sign_info.get("sign_cnt_missed", 0)

    lines = []
    lines.append("<b>🎮 Genshin Impact Daily Report</b>")
    lines.append(f"<i>@{user_name}</i>")
    lines.append("")
    lines.append(f"📅 {now.strftime('%d/%m/%Y')} • ⏰ {now.strftime('%H:%M')} (UTC+8)")
    lines.append("")

    # สถานะวันนี้
    if already_signed:
        lines.append("✅ <b>Status:</b> Already checked in today")
    else:
        lines.append("✅ <b>Status:</b> Check-in successful")

    # รางวัลวันนี้
    if today_reward:
        lines.append("")
        lines.append(f"🎁 <b>Today's Reward:</b>")
        lines.append(f"   {today_reward.get('name', '-')} ×{today_reward.get('cnt', 0)}")

    # รางวัลพรุ่งนี้
    if tomorrow_reward:
        lines.append(f"")
        lines.append(f"🎁 <b>Tomorrow's Reward (Preview):</b>")
        lines.append(f"   {tomorrow_reward.get('name', '-')} ×{tomorrow_reward.get('cnt', 0)}")

    # สถิติเดือนนี้
    lines.append("")
    lines.append(f"📊 <b>This Month:</b>")
    lines.append(f"   ✔ Checked in: {total_sign_days} day(s)")
    lines.append(f"   ✘ Missed: {missed_days} day(s)")

    # สรุปรางวัลทั้งเดือน
    if rewards and total_sign_days > 0:
        monthly = summarize_monthly_rewards(rewards, total_sign_days)
        if monthly:
            lines.append("")
            lines.append(f"💎 <b>Monthly Rewards Summary:</b>")
            for item_name, qty in monthly.items():
                lines.append(f"   • {item_name} ×{qty}")

    # เช็คอินครั้งถัดไป
    lines.append("")
    lines.append(f"🔄 <b>Next Check-in:</b>")
    lines.append(f"   {tmrw.strftime('%d/%m/%Y')} at 07:00 (UTC+8)")

    # แจ้งเตือน Cookie ใกล้หมดอายุ
    if is_cookie_expiring_soon():
        lines.append("")
        lines.append(f"⚠️ <b>Warning:</b> Cookie expires soon!")
        lines.append(f"   Please update in GitHub Secrets")

    return "\n".join(lines)


def send_telegram(token, chat_id, message):
    if not token or not chat_id:
        logger.info("Telegram not configured")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        res = requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=10)
        logger.info(f"Telegram: {res.status_code}")
    except Exception as e:
        logger.error(f"Telegram error: {str(e)}")


def process_user(user_config, user_agent):
    user_name = user_config.get("name", "Unknown")
    uid = user_config.get("uid")
    server = user_config.get("server", "os_asia")
    cookie = user_config.get("cookie")
    telegram_token = user_config.get("telegram_token")
    telegram_chat_id = user_config.get("telegram_chat_id")

    logger.info(f"Processing user: {user_name}")

    try:
        # ดึงข้อมูล
        sign_info = get_sign_info(cookie, user_agent)
        if not sign_info:
            raise Exception("Failed to get sign info")

        already_signed = sign_info.get("is_sign", False)
        total_sign_days = sign_info.get("total_sign_day", 0)

        # ดึงรายการรางวัล
        rewards = get_reward_list(cookie, user_agent)

        # รางวัลวันนี้และพรุ่งนี้
        today_idx = total_sign_days - 1 if already_signed else total_sign_days
        tmrw_idx = today_idx + 1

        today_reward = rewards[today_idx] if rewards and 0 <= today_idx < len(rewards) else None
        tomorrow_reward = rewards[tmrw_idx] if rewards and 0 <= tmrw_idx < len(rewards) else None

        # Check-in ถ้ายังไม่ได้ทำ
        if not already_signed:
            result = do_sign(cookie, user_agent)
            if result.get("retcode") != 0:
                raise Exception(f"Check-in failed: {result.get('message', 'Unknown error')}")

        # สร้าง report
        report = build_report(user_name, sign_info, rewards, today_reward, tomorrow_reward, already_signed)

        logger.info(f"\n{report}")
        send_telegram(telegram_token, telegram_chat_id, report)

        return True

    except Exception as e:
        message = f"Genshin check-in error for {user_name}: {str(e)}"
        logger.error(message)
        send_telegram(
            user_config.get("telegram_token"),
            user_config.get("telegram_chat_id"),
            message
        )
        return False


def main():
    users_config_json = os.getenv("USERS_CONFIG")
    user_agent = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    if not users_config_json:
        logger.error("USERS_CONFIG is required")
        sys.exit(1)

    try:
        users_config = json.loads(users_config_json)
        if not isinstance(users_config, list):
            users_config = [users_config]
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in USERS_CONFIG: {str(e)}")
        sys.exit(1)

    logger.info(f"Processing {len(users_config)} user(s)")

    success_count = 0
    for user_config in users_config:
        if process_user(user_config, user_agent):
            success_count += 1

    logger.info(f"Completed: {success_count}/{len(users_config)} successful")

    sys.exit(0 if success_count == len(users_config) else 1)


if __name__ == "__main__":
    main()
