from contextlib import contextmanager
import os

from dotenv import load_dotenv


HOST = "fxcorporate.com/Hosts.jsp"
CONNECTION = "Real"


def get_credentials():
    """从环境变量读取用户名和密码。"""
    load_dotenv()
    user = os.getenv("user_name")
    pwd = os.getenv("password")
    return user, pwd


def session_status_changed(session, status):
    print("Trading session status: " + str(status))


@contextmanager
def forexconnect_session():
    user_name, password = get_credentials()
    if not user_name or not password:
        raise RuntimeError("Missing credentials")
    from forexconnect import ForexConnect

    fx = ForexConnect()
    try:
        try:
            fx.login(
                user_name,
                password,
                HOST,
                CONNECTION,
                session_status_callback=session_status_changed,
            )
        except Exception as exc:
            try:
                fx.logout()
            except Exception:
                pass
            raise RuntimeError(f"ForexConnect login failed: {exc}") from exc
        yield fx
    finally:
        try:
            fx.logout()
        except Exception:
            pass
