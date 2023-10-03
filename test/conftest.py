from pathlib import Path
import shutil


def pytest_configure(config):
    """
    Allows plugins and conftest files to perform initial configuration.
    This hook is called for every plugin and initial conftest
    file after command line options have been parsed.
    """
    ...


def pytest_sessionstart(session):
    """
    Called after the Session object has been created and
    before performing collection and entering the run test loop.
    """
    # remove the tmp folder to empty old results
    p = Path(__file__).parent.parent / 'tmp'
    if p.exists() and p.is_dir():
        shutil.rmtree(p)
    p.mkdir(exist_ok=True)


def pytest_sessionfinish(session, exitstatus):
    """
    Called after whole test run finished, right before
    returning the exit status to the system.
    """
    ...


def pytest_unconfigure(config):
    """
    called before test process is exited.
    """
    ...
