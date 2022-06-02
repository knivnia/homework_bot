import logging
import os
import sys
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telegram import Bot, TelegramError

from exceptions import ConnectionError, EndpointError


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

HOMEWORK_KEYS = (
    'id',
    'status',
    'homework_name',
    'reviewer_comment',
    'date_updated',
    'lesson_name'
)

REQUEST = {
    'url': ENDPOINT,
    'headers': HEADERS,
    'params': {'from_date': int(time.time())}
}


def send_message(bot, message):
    """Send message in Telegram chat."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except TelegramError:
        raise TelegramError(f'Message has not been sent. {sys.exc_info}.')
    else:
        logging.info('Message has been sent.')


def get_api_answer(current_timestamp):
    """Get response from API."""
    REQUEST['params'] = {'from_date': current_timestamp}
    try:
        response = requests.get(
            REQUEST['url'],
            headers=REQUEST['headers'],
            params=REQUEST['params']
        )
        if response.status_code != HTTPStatus.OK:
            raise ConnectionError(
                f'Wrong page status: {response.status_code}'
            )
        response = response.json()
        return response
    except EndpointError as error:
        raise EndpointError(f'API is not available, {error}.')


def check_response(response):
    """Check API response."""
    logger.info('Beginning to check API response.')
    if not isinstance(response, dict):
        raise TypeError('Wrong data type (dict)!')
    if response.get('homeworks') is None:
        raise IndexError('Homeworks not in response.')
    if response.get('current_date') is None:
        raise IndexError('Current date not in response.')
    homework = response.get('homeworks')
    if not isinstance(homework, list):
        raise TypeError('Wrong data type (list)!')
    return homework


def parse_status(homework):
    """Get homework status from API response."""
    homework_name = homework['homework_name']
    if homework_name is None:
        raise IndexError('No homework name in response.')
    homework_status = homework['status']
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
    if check_tokens() is False:
        logger.critical('Tokens are missing!')
        sys.exit('Tokens are missing!')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if len(homework) > 0:
                message = parse_status(homework[0])
                send_message(bot, message)
            else:
                logger.debug('No updates.')
            current_timestamp = response.get('current_date', current_timestamp)
            time.sleep(RETRY_TIME)
        except Exception as error:
            logger.error(f'Error: {error}')
            message = f'Error: {error}'
            bot.send_message(TELEGRAM_CHAT_ID, message)
            time.sleep(RETRY_TIME)


if not logging.getLogger().hasHandlers():
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
    logger = logging.getLogger(__name__)
else:
    logger = logging.getLogger()

if __name__ == '__main__':
    main()
