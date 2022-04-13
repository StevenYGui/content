#!/usr/bin/python3
import collections
import argparse
import os
import json

# NOTE: This is not to be confused with the https://pypi.org/project/ssg/
# package. The ssg package we're referencing here is actually a relative import
# within this repository. Because of this, you need to ensure
# ComplianceAsCode/content/ssg is discoverable from PYTHONPATH before you
# invoke this script.
try:
    from ssg import controls
    import ssg.products
except ModuleNotFoundError as e:
    # NOTE: Only emit this message if we're dealing with an import error for
    # ssg. Since the local ssg module imports other things, like PyYAML, we
    # don't want to emit misleading errors for legit dependencies issues if the
    # user hasn't installed PyYAML or other transitive dependencies from ssg.
    # We should revisit this if or when we decide to implement a python package
    # management strategy for the python scripts provided in this repository.
    if e.name == 'ssg':
        msg = """Unable to import local 'ssg' module.

The 'ssg' package from within this repository must be discoverable before
invoking this script. Make sure the top-level directory of the
ComplianceAsCode/content repository is available in the PYTHONPATH environment
variable (example: $ export PYTHONPATH=($pwd)).
"""
        raise RuntimeError(msg) from e
    raise


SSG_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def print_options(opts):
    if len(opts) > 0:
        print("Available options are:\n - " + "\n - ".join(opts))
    else:
        print("The controls file is not written appropriately.")


def validate_args(ctrlmgr, args):
    """ Validates that the appropriate args were given
        and that they're valid entries in the control manager."""

    policy = None
    try:
        policy = ctrlmgr._get_policy(args.id)
    except ValueError as e:
        print("Error: ", e)
        print_options(ctrlmgr.policies.keys())
        exit(1)

    try:
        policy.get_level_with_ancestors_sequence(args.level)
    except ValueError as e:
        print("Error: ", e)
        print_options(policy.levels_by_id.keys())
        exit(1)


def calculate_stats(ctrls):
    total = len(ctrls)
    ctrlstats = collections.defaultdict(int)
    ctrllist = collections.defaultdict(set)

    if total == 0:
        print("No controls founds with the given inputs. Maybe try another level.")
        exit(1)

    for ctrl in ctrls:
        ctrlstats[str(ctrl.status)] += 1
        ctrllist[str(ctrl.status)].add(ctrl)

    applicable = total - ctrlstats[controls.Status.NOT_APPLICABLE]
    assessed = ctrlstats[controls.Status.AUTOMATED] + ctrlstats[controls.Status.SUPPORTED] + \
        ctrlstats[controls.Status.DOCUMENTATION] + ctrlstats[controls.Status.INHERENTLY_MET] + \
        ctrlstats[controls.Status.PARTIAL]

    print("Total controls = {total}".format(total=total))
    print_specific_stat("Applicable", applicable, total)
    print_specific_stat("Assessed", assessed, applicable)
    print()
    print_specific_stat("Automated",
                        ctrlstats[controls.Status.AUTOMATED],
                        applicable)
    print_specific_stat("Manual",
                        ctrlstats[controls.Status.MANUAL],
                        applicable)
    print_specific_stat("Supported",
                        ctrlstats[controls.Status.SUPPORTED],
                        applicable)
    print_specific_stat("Documentation",
                        ctrlstats[controls.Status.DOCUMENTATION],
                        applicable)
    print_specific_stat("Inherently Met",
                        ctrlstats[controls.Status.INHERENTLY_MET],
                        applicable)
    print_specific_stat("Does Not Meet",
                        ctrlstats[controls.Status.DOES_NOT_MEET],
                        applicable)
    print_specific_stat("Partial",
                        ctrlstats[controls.Status.PARTIAL],
                        applicable)

    applicablelist = ctrls - ctrllist[controls.Status.NOT_APPLICABLE]
    assessedlist = set().union(ctrllist[controls.Status.AUTOMATED]).union(ctrllist[controls.Status.SUPPORTED])\
        .union(ctrllist[controls.Status.DOCUMENTATION]).union(ctrllist[controls.Status.INHERENTLY_MET])\
        .union(ctrllist[controls.Status.PARTIAL]).union(ctrllist[controls.Status.MANUAL])
    print("Missing:", ", ".join(sorted(str(c.id)
          for c in applicablelist - assessedlist)))


def print_specific_stat(stat, current, total):
    print("{stat} = {percent}% -- {current} / {total}".format(
        stat=stat,
        percent=round((current / total) * 100.00, 2),
        current=current,
        total=total))


def stats(ctrlmgr, args):
    validate_args(ctrlmgr, args)
    ctrls = set(ctrlmgr.get_all_controls_of_level(args.id, args.level))
    total = len(ctrls)

    if total == 0:
        print("No controls founds with the given inputs. Maybe try another level.")
        exit(1)

    if args.output_format == 'json':
        print_to_json(
            ctrls,
            args.product,
            args.id,
            args.level)
    else:
        calculate_stats(ctrls)


def print_to_json(ctrls, product, id, level):
    data = dict()
    ctrllist = collections.defaultdict(set)

    for ctrl in ctrls:
        ctrllist[str(ctrl.status)].add(ctrl)

    applicablelist = ctrls - ctrllist[controls.Status.NOT_APPLICABLE]
    assessedlist = set().union(ctrllist[controls.Status.AUTOMATED]).union(ctrllist[controls.Status.SUPPORTED])\
        .union(ctrllist[controls.Status.DOCUMENTATION]).union(ctrllist[controls.Status.INHERENTLY_MET])\
        .union(ctrllist[controls.Status.PARTIAL]).union(ctrllist[controls.Status.MANUAL])

    data["format_version"] = "v0.0.1"
    data["product_name"] = product
    data["benchmark"] = dict()
    data["benchmark"]["name"] = id
    data["benchmark"]["baseline"] = level
    data["total_controls"] = len(applicablelist)
    data["addressed_controls"] = dict()
    data["addressed_controls"]["all"] = get_id_array(ctrls)
    data["addressed_controls"]["applicable"] = get_id_array(applicablelist)
    data["addressed_controls"]["assessed"] = get_id_array(assessedlist)
    data["addressed_controls"]["inherently"] = get_id_array(
        ctrllist[controls.Status.INHERENTLY_MET])
    data["addressed_controls"]["manual"] = get_id_array(
        ctrllist[controls.Status.MANUAL])
    data["addressed_controls"]["supported"] = get_id_array(
        ctrllist[controls.Status.SUPPORTED])
    data["addressed_controls"]["automated"] = get_id_array(
        ctrllist[controls.Status.AUTOMATED])
    data["addressed_controls"]["notapplicable"] = get_id_array(
        ctrllist[controls.Status.NOT_APPLICABLE])
    data["addressed_controls"]["partial"] = get_id_array(
        ctrllist[controls.Status.PARTIAL])
    data["addressed_controls"]["pending"] = get_id_array(
        ctrllist[controls.Status.PENDING])
    data["addressed_controls"]["notassessed"] = get_id_array(
        applicablelist - assessedlist)
    print(json.dumps(data))


subcmds = dict(
    stats=stats
)


def get_id_array(ctrls):
    return [c.id for c in ctrls]


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--controls-dir",
        help=("Directory that contains control files with policy controls. "
              "e.g.: ~/scap-security-guide/controls"),
        default="./controls/",
    )
    subparsers = parser.add_subparsers(dest="subcmd", required=True)
    statsparser = subparsers.add_parser(
        'stats',
        help="calculate and return the statistics for the given benchmark")
    statsparser.add_argument(
        "-i", "--id",
        help="the ID or name of the controls file in the controls/ directory",
        required=True)
    statsparser.add_argument(
        "-l", "--level",
        help="the compliance target level to analyze",
        required=True)
    statsparser.add_argument(
        "-p", "--product", help="product to check has required references")
    statsparser.add_argument(
        "-o",
        "--output-format",
        choices=['json'],
        help="The output format of the report")
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()
    product_base = os.path.join(SSG_ROOT, "products", args.product)
    product_yaml = os.path.join(product_base, "product.yml")
    env_yaml = ssg.products.load_product_yaml(product_yaml)
    controls_manager = controls.ControlsManager(
        args.controls_dir, env_yaml=env_yaml)
    controls_manager.load()
    subcmds[args.subcmd](controls_manager, args)


if __name__ == "__main__":
    main()
