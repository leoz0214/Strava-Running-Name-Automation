"""
Module to generate the title and description of a particular
activity if possible, based on the configuration details.
"""
import activity
import configure


def generate_title_and_description(
    activity_: activity.Activity, config: configure.Config
) -> tuple[str, str]:
    """
    Given an activity and the config info, a title and description is generated
    using a suitable template if possible. If a title and description cannot
    be generated, an error is raised.
    """
    # TODO