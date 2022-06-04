import logging
import os
import sys
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telegram import Bot

from exceptions import EndpointError, MessageError, DateError

logger = logging.getLogger(__name__)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Send message in Telegram chat."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except MessageError:
        raise MessageError(
            f'Message "{message}" has not been sent. {sys.exc_info}.'
        )
    else:
        logging.info('Message has been sent.')


def get_api_answer(current_timestamp):
    """Get response from API."""
    request = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': int(time.time())}
    }
    request['params'] = {'from_date': current_timestamp}
    url, headers, params = request.values()
    error_message = f'API {url} is not available.'
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != HTTPStatus.OK:
            error_message = f'Wrong page status: {response.status_code}'
            raise Exception
        return response.json()
    except Exception:
        raise EndpointError(error_message)


def check_response(response):
    """Check API response."""
    logger.info('Beginning to check API response.')
    homework = response['homeworks']
    if not isinstance(response, dict):
        raise TypeError('Wrong data type (dict)!')
    if homework is None:
        raise KeyError('Homeworks not in response.')
    if response['current_date'] is None:
        raise DateError('Current date not in response.')
    if not isinstance(homework, list):
        raise TypeError('Wrong data type (list)!')
    return homework


def parse_status(homework):
    """Get homework status from API response."""
    try:
        homework_name = homework['homework_name']
    except KeyError:
        raise KeyError('No homework name in response.')
    try:
        homework_status = homework['status']
    except KeyError:
        raise KeyError('No homework status in response.')
    if homework_status not in HOMEWORK_VERDICTS:
        raise IndexError('Unexpected homework status.')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Check tokens in .env."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Bot logic."""
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if not check_tokens():
        logger.critical('Tokens are missing!')
        sys.exit('Tokens are missing!')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if len(homework) > 0:
                message = parse_status(homework.pop())
                send_message(bot, message)
            else:
                logger.info('No updates.')
            current_timestamp = response.get('current_date', current_timestamp)
        except Exception as error:
            if isinstance(error, [MessageError, DateError]):
                logger.error(message, exc_info=True)
            else:
                message = f'Error: {error}'
                logger.error(message)
                bot.send_message(TELEGRAM_CHAT_ID, message)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[
            logging.FileHandler(os.path.basename('/root/homework.log'), 'w'),
            logging.StreamHandler(sys.stdout)],
        format=(
            '%(asctime)s -'
            ' %(name)s -'
            ' %(levelname)s -'
            ' %(funcName)s -'
            ' %(levelno)s -'
            ' %(message)s'
        )
    )
    main()
