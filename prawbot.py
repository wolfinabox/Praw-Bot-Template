import praw  # The Reddit API
# Necessary exceptions to catch
from prawcore.exceptions import OAuthException, ResponseException
# To truncate messages (optional really)
from wolfinaboxutils.formatting import truncate
import time  # To sleep
import json  # Save/Load config
import logging  # For logging... of course
import sys  # For various things
# Configure the logger
logger = logging.getLogger('redditbot')
logger.addHandler(logging.FileHandler(f'{__name__}.log'))
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.DEBUG)

#GLOBALS===========================#
config = {}
default_config = {'owner': 'owner_username_here', 'username': 'bot_username_here', 'password': 'bot_password_here',
                  'client_id': 'bot_client_id_here', 'client_secret': 'bot_client_secret_here', 'user_agent': 'descriptive bot message here',
                  'subreddits': [], 'unsubscribed_users': []}
#==================================#
#Functions=========================#


def save():
    """
    Save the config to file
    """
    # Open "config.json" and dump the config to it
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4, separators=(',', ': '))


def footer_message(bot: praw.Reddit):
    """
    Returns the constructed footer message.\n
    `bot` The currently running bot.
    """
    # This can be customised to whatever you like. You can use Reddit markdown formatting as well.
    return f'\n\n___\n\n*^I ^am ^a ^bot. ^Message ^u/{config["owner"]} ^if ^I ^am ^being ^stupid. ^[Unsubscribe](https://www.reddit.com/message/compose/?to={str(bot.user.me())}&subject=unsubscribe&message=unsubscribe)*'


def login():
    # Try loading the config and logging in
    try:
        global config
        with open('config.json', 'r') as f:
            config = json.load(f)
        # This block creates the Reddit api connection.
        r = praw.Reddit(username=config['username'], password=config['password'],
                        client_id=config['client_id'], client_secret=config['client_secret'],
                        user_agent=config['user_agent'])

        # Check credentials (if we can get "me", we're logged in!)
        r.user.me()
        return r
    # Config file doesn't exist
    except FileNotFoundError:
        logger.warn(
            'Couldn\'t find "config.json", creating...\nPlease edit "config.json" and fill in the variables with your information.')
        with open('config.json', 'w') as f:
            json.dump(default_config, f, indent=4, separators=(',', ': '))
    # Couldn't log in to Reddit (probably wrong credentials)
    except (OAuthException, ResponseException) as e:
        logger.error(
            'Invalid credentials.\nPlease check that the credentials in "config.json" are correct.\n('+str(e)+')')
    input('Press return to exit...')
    exit(0)


def handle_comments(bot: praw.Reddit, max_comments: int = 25):
    """
    Handle comments\n
    `bot` The currently running bot\n
    `max_comments` How many comments to search through (for each sub)
    """
    # For every subreddit bot should comment on
    for subreddit in config['subreddits']:
        # For every comment in that subreddit
        for comment in bot.subreddit(subreddit).comments(limit=max_comments):
            # Don't reply to ourself
            if comment.author == bot.user.me():
                continue
            # Don't reply to unsubscribed users
            if comment.author in config['unsubscribed_users']:
                continue
            # Get Replies (this needs to be done, otherwise replies are not requested)
            comment.refresh()
            # Don't reply to the same post more than once
            if bot.user.me() in [comment.author for comment in comment.replies]:
                continue

            # Start Matching Text
            # EXAMPLE: This will match the word 'test' in a comment (.lower() so TEST or tEsT is also matched)
            if 'test' in comment.body.lower():
                logger.info('Found matching comment "'+comment.id+'" in subreddit "' +
                            subreddit+'"\n\t"'+truncate(comment.body, 70, '...')+'"')
                # This is how you reply
                comment.reply(f'I found this comment!{footer_message(bot)}')


def handle_messages(bot: praw.Reddit, max_messages: int = 25):
    """
    Handle messages to the bot\n
    `bot` The currently running bot
    `max_messages` How many messages to search through
    """
    # Get the messages
    messages = list(bot.inbox.messages(limit=max_messages))
    # If we have no messages, quit
    if len(messages) == 0:
        return
    # Print how many messages we have
    logger.info('Messages ('+str(len(messages))+'):')
    # Iterate through every message
    for message in messages:
        logger.info('Sender: '+(str(message.author)
                                if message.author else 'Reddit'))
        logger.info('\t"'+truncate(message.body, 70, '...')+'"')

        # This is where you can handle different text in the messages.
        # Unsubscribe user
        if 'unsubscribe' in message.subject.lower() or 'unsubscribe' in message.body.lower():
            logger.info(f'Unsubscribing "{message.author}"')
            config['unsubscribed_users'].append(str(message.author))
            save()
            message.reply(
                f'Okay, I will no longer reply to your posts.{footer_message(bot)}')
            message.delete()
        # Ignore the message if we don't recognise it
        else:
            message.delete()


def run_bot(bot: praw.Reddit, sleep_time: int = 10):
    handle_comments(bot)
    handle_messages(bot)
    # Sleep, to not flood
    logger.debug('Sleeping '+str(sleep_time)+' seconds...')
    time.sleep(sleep_time)
#==================================#


#Main Code=========================#
if __name__ == '__main__':
    logger.info('Logging in...')
    bot = login()

    logger.info('Logged in as '+str(bot.user.me()))
    logger.info('Active in '+str(len(config['subreddits']))+' subreddit'+('s'if len(config['subreddits']) != 1 else '')+': ' +
                (', '.join([sub for sub in config['subreddits']])))
    logger.info(str(len(config['unsubscribed_users']))+' unsubscribed user' +
                ('s'if len(config['unsubscribed_users']) != 1 else ''))

    while True:
        run_bot(bot)
#==================================#
