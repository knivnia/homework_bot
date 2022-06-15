import logging
import os
import sys
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telegram import Bot, TelegramError

from exceptions import ErrorEventNotForSending

logger = logging.getLogger(__name__)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Homework is approved by reviewer. Congratulations!',
    'reviewing': 'Reviewer is checking your homework.',
    'rejected': 'Homework is checked: need to fix something.'
}


def send_message(bot, message):
    """Send message in Telegram chat."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except TelegramError:
        raise ErrorEventNotForSending(
            f'Message "{message}" has not been sent.'
        )
    else:
        logging.info('Message has been sent.')


def get_api_answer(current_timestamp):
    """Get response from API."""
    request = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': current_timestamp}
    }
    base_error_message = (
        f'API "{request["url"]}" with headers: '
        f'"{request["headers"]}" and params:'
        f'"{request["params"]}"'
    )
    try:
        response = requests.get(**request)
        if response.status_code != HTTPStatus.OK:
            error_message = (
                f'{base_error_message} returned wrong '
                f'page status: {response.status_code}.'
            )
            raise ConnectionError(error_message)
        return response.json()
    except Exception:
        raise ConnectionError(f'{base_error_message} is not available.')


def check_response(response):
    """Check API response."""
    logger.info('Beginning to check API response.')
    if not isinstance(response, dict):
        raise TypeError('Wrong data type (dict)!')
    homeworks = response.get('homeworks')
    if homeworks is None:
        raise KeyError('Homeworks not in response.')
    if not isinstance(homeworks, list):
        raise TypeError('Wrong data type (list)!')
    if response.get('current_date') is None:
        raise ErrorEventNotForSending('Current date not in response.')
    return homeworks


def parse_status(homeworks):
    """Get homework status from API response."""
    homework_name = homeworks.get('homework_name')
    if homework_name is None:
        raise KeyError('No homework name in response.')
    homework_status = homeworks.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Unexpected homework status: "{homework_status}".')
    verdict = HOMEWORK_VERDICTS[homework_status]
    comment = homeworks.get('reviewer_comment')
    return (
        f'Homework "{homework_name}" status is changed. {verdict} '
        f'Comment by reviewer: "{comment}"'
    )


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
            homeworks = check_response(response)
            if len(homeworks) > 0:
                message = parse_status(homeworks.pop())
                send_message(bot, message)
            else:
                logger.info('No updates.')
            current_timestamp = response.get('current_date', current_timestamp)
        except ErrorEventNotForSending as error:
            logger.error(f'Error: {error}', exc_info=True)
        except Exception as error:
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
