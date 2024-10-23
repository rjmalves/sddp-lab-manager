import time
from multiprocessing import Manager

import click

from app.handlers.case_running import CaseRunning
from app.handlers.deck_editing import DeckEditing
from app.handlers.result_processing import ResultProcessing
from app.utils.log import Log


@click.group()
def app():
    """
    App for editing and running sddp-lab
    deck variations.
    """
    pass


@click.command("edit")
@click.argument("config_json", type=str)
def edit(config_json):
    """
    Edits and generates decks by altering parameters
    """

    m = Manager()
    q = m.Queue(-1)
    Log.start_logging_process(q)
    logger = Log.configure_main_logger(q)
    logger.info("### sddp-lab-manager - EDIT ###")

    try:
        handler = DeckEditing()
        handler.handle(config_json)
    except Exception as e:
        logger.exception(str(e))
    finally:
        logger.info("### END ###")
        time.sleep(1.0)
        Log.terminate_logging_process()


app.add_command(edit)


@click.command("run")
@click.argument("config_json", type=str)
def run(config_json):
    """
    Runs parallelizing a series of sddp-lab decks
    """

    m = Manager()
    q = m.Queue(-1)
    Log.start_logging_process(q)
    logger = Log.configure_main_logger(q)
    logger.info("### sddp-lab-manager - RUN ###")

    try:
        handler = CaseRunning()
        handler.handle(config_json, q)
    except Exception as e:
        logger.exception(str(e))
    finally:
        logger.info("### END ###")
        time.sleep(1.0)
        Log.terminate_logging_process()


app.add_command(run)


@click.command("postprocess")
@click.argument("config_json", type=str)
def postprocess(config_json):
    """
    Groups and processes results from sddp-lab cases
    """

    m = Manager()
    q = m.Queue(-1)
    Log.start_logging_process(q)
    logger = Log.configure_main_logger(q)
    logger.info("### sddp-lab-manager - POSTPROCESS ###")

    try:
        handler = ResultProcessing()
        handler.handle(config_json)
    except Exception as e:
        logger.exception(str(e))
    finally:
        logger.info("### END ###")
        time.sleep(1.0)
        Log.terminate_logging_process()


app.add_command(postprocess)
