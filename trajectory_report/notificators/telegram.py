import requests
from trajectory_report.config import TOKEN_TELEGRAM, TELEGRAM_ADMIN_ID


def notify_admin(text: str) -> int:
    """
    Присылает в лс администратору сообщение с текстом.
    Возвращает status_code запроса, чтобы понять, дошло ли сообщение.
    """
    api_url = "https://api.telegram.org/bot{}/".format(TOKEN_TELEGRAM)
    parse_mode = 'MarkDown'
    method = 'sendMessage'
    params = {'chat_id': TELEGRAM_ADMIN_ID,
              'parse_mode': parse_mode,
              'text': text}
    resp = requests.post(api_url + method, params)
    return resp.status_code
