#!/usr/bin/env python3

import os
import sys
import json
import requests
import logging
import hashlib
import secrets
import string
import time
from html import escape
from datetime import datetime, timedelta, timezone

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SIGN_URL    = "https://sg-hk4e-api.hoyolab.com/event/sol/sign"
INFO_URL    = "https://sg-hk4e-api.hoyolab.com/event/sol/info"
REWARD_URL  = "https://sg-hk4e-api.hoyolab.com/event/sol/home"
GAME_URL    = "https://sg-public-api.hoyolab.com/event/game_record/genshin/api/dailyNote"
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


class ResinError(Exception):
    """A safe, actionable diagnostic for the daily-note request."""


def get_resin_info(uid, server, cookie, user_agent):
    if not uid or not str(uid).isdigit():
        raise ResinError("Set a valid game UID in USERS_CONFIG.")
    if server not in {"os_asia", "os_cht", "os_euro", "os_usa"}:
        raise ResinError("Unsupported server in USERS_CONFIG.")
    if not cookie:
        raise ResinError("Set the HoYoLAB cookie in USERS_CONFIG.")

    # Overseas Battle Chronicle request format, as used by genshin.py.
    timestamp = int(time.time())
    nonce = "".join(secrets.choice(string.ascii_letters) for _ in range(6))
    digest = hashlib.md5(
        f"salt=6s25p5ox5y14umn1p61aqyyvbvvl3lrt&t={timestamp}&r={nonce}".encode()
    ).hexdigest()
    headers = get_headers(cookie, user_agent)
    headers.update({
        "DS": f"{timestamp},{nonce},{digest}",
        "x-rpc-app_version": "1.5.0",
        "x-rpc-client_type": "5",
        "x-rpc-language": "en-us",
        "x-rpc-lang": "en-us",
        "Referer": "https://www.hoyolab.com/",
        "Origin": "https://www.hoyolab.com",
        "Accept-Encoding": "gzip, deflate",
    })
    try:
        res = requests.get(
            GAME_URL, params={"role_id": str(uid), "server": server},
            headers=headers, timeout=10,
        )
        if res.status_code != 200:
            raise ResinError(f"Resin API HTTP {res.status_code}; try again later.")
        payload = res.json()
        if not isinstance(payload, dict):
            raise ValueError("Invalid response")
        code = payload.get("retcode")
        if code != 0:
            hints = {
                -100: "HoYoLAB cookie is invalid or expired; refresh it in GitHub Secrets.",
                10001: "HoYoLAB authentication failed; refresh the cookie in GitHub Secrets.",
                10102: "Enable Real-Time Notes in HoYoLAB Battle Chronicle and use the account owning this UID.",
            }
            hint = hints.get(code, "Check HoYoLAB Battle Chronicle, the account cookie, UID and server.")
            if code in {1034, 10035, 10041, 5003}:
                hint = "Complete the verification in HoYoLAB, then try again."
            raise ResinError(f"Resin API retcode {code}: {hint}")
        data = payload["data"]
        current = int(data["current_resin"])
        maximum = int(data["max_resin"])
        recovery = int(data["resin_recovery_time"])
        if current < 0 or maximum <= 0 or recovery < 0:
            raise ValueError("Invalid resin values")
        return {"current_resin": current, "max_resin": maximum,
                "resin_recovery_time": recovery}
    except requests.RequestException as exc:
        raise ResinError("Cannot reach Resin API; try again later.") from exc
    except (ValueError, KeyError, TypeError) as exc:
        raise ResinError("Resin API returned an unexpected response.") from exc


def do_sign(cookie, user_agent):
    headers = get_headers(cookie, user_agent)
    res = requests.post(f"{SIGN_URL}?act_id={ACT_ID}", headers=headers, timeout=10)
    data = res.json()
    logger.info(f"Sign response: {data.get('retcode')}")
    return data


def calculate_resin_recovery_time(recovery_seconds):
    return datetime.now(UTC8) + timedelta(seconds=recovery_seconds)


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


def build_report(user_name, sign_info, rewards, today_reward, tomorrow_reward, already_signed, resin_info=None, resin_error=None):
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

    lines.extend(["", "🌙 <b>Resin Status:</b>"])
    if resin_info:
        current = resin_info["current_resin"]
        maximum = resin_info["max_resin"]
        lines.append(f"   Current: {current}/{maximum}")
        if current >= maximum:
            lines.append("   Resin is full!")
        else:
            seconds = resin_info["resin_recovery_time"]
            full_at = calculate_resin_recovery_time(seconds)
            minutes = (seconds + 59) // 60
            lines.append(f"   Full at: {full_at:%d/%m %H:%M} (UTC+8)")
            lines.append(f"   In {minutes // 60}h {minutes % 60}m")
    else:
        lines.append(f"   Unavailable: {escape(resin_error or 'No data returned.')}")

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

        resin_info = None
        resin_error = None
        try:
            resin_info = get_resin_info(uid, server, cookie, user_agent)
        except ResinError as exc:
            resin_error = str(exc)
            logger.warning("Resin unavailable: %s", resin_error)

        # สร้าง report
        report = build_report(user_name, sign_info, rewards, today_reward, tomorrow_reward, already_signed, resin_info, resin_error)

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
