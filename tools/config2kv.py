# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""
Config2kv - extracts config-based secrets and stores them in KeyVault.

The tool reads settings from the current msticpyconfig.yaml. It will read
the current file specified by the MSTICPYCONFIG file or a path specified by
the --path argument.

For each provider secrets are extracted from the Args subkeys. Keyvault
secrets are built using the pathname of the setting and the secret value.
By default, most KeyVault settings are read from the settings file itself.
These can be supplied by command line arguments. Commandline arguments
will override settings in the config file.

If the vault name specified does not exist in the subscription it will be
created in the specified resource group and region. The secrets will then
be stored in the vault using the name/secret pairs mentioned earlier.

Finally, a version of the settings file, updated to reference the KeyVault
values, is written to the file specified in the --output argument.

--show will perform the parsing of the settings file but do not updates.
--verbose will show more details of the changes that are being made.

"""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
from pprint import pprint
import re
import sys
import yaml

from msrestazure.azure_exceptions import CloudError

from msticpy.common.keyvault_client import (
    BHKeyVaultClient,
    BHKeyVaultMgmtClient,
    KeyVaultSettings,
)
from msticpy.common import pkg_config as config

try:
    from .toollib import VERSION  # type: ignore

    __version__ = VERSION
except ImportError:
    pass

__author__ = "Ian Hellen"


_KV_PLACE_HOLDER = {"KeyVault": None}


def _read_config_settings(conf_file):
    try:
        sys_config = os.environ["MSTICPYCONFIG"]
    except KeyError:
        sys_config = Path.cwd().joinpath("msticpyconfig.yaml")
    if not conf_file:
        conf_file = sys_config
    if not conf_file:
        raise ValueError("Configuration file not found.")

    with open(conf_file, "r") as conf_hdl:
        cur_settings = yaml.safe_load(conf_hdl)

    # temporarily set env var to point to conf_file
    os.environ["MSTICPYCONFIG"] = conf_file
    config.refresh_config()
    kvlt_settings = KeyVaultSettings()
    os.environ["MSTICPYCONFIG"] = sys_config
    return cur_settings, kvlt_settings


def _write_config_settings(conf_file, conf_settings, confirm):
    if Path(conf_file).is_file():
        print(f"Output file {conf_file} exists.")
        if not _prompt_yn("Overwrite (y/n)?", confirm):
            return
    yaml.SafeDumper.ignore_aliases = lambda *args: True
    with open(conf_file, "w") as conf_hdl:
        yaml.safe_dump(data=conf_settings, stream=conf_hdl)


def _format_kv_name(setting_path):
    """Return normalized name for use as a KeyVault secret name."""
    return re.sub("[^0-9a-zA-Z-]", "-", setting_path)


def _get_config_secrets(cur_settings, section_name):
    kv_dict = {}
    ud_settings = deepcopy(cur_settings[section_name])
    for prov, setting in cur_settings[section_name].items():
        if "Args" in setting:
            arg_path = f"{section_name}.{prov}.Args"
            for arg, arg_val in setting["Args"].items():
                if arg not in ["AuthKey", "ApiID"]:
                    continue
                item_path = arg_path + "." + arg
                if isinstance(arg_val, str):
                    kv_dict[_format_kv_name(item_path)] = arg_val
                elif isinstance(arg_val, dict):
                    if "KeyVault" in arg_val:
                        continue
                    if "EnvironmentVar" in arg_val:
                        env_var_name = arg_val["EnvironmentVar"]
                        env_value = os.environ.get(env_var_name)
                        kv_dict[_format_kv_name(item_path)] = env_value
                ud_settings[prov]["Args"][arg] = _KV_PLACE_HOLDER
    return kv_dict, ud_settings


def _transform_settings(cur_settings):
    ud_settings = deepcopy(cur_settings)
    kv_secrets_dict = {}

    for section in ["TIProviders", "OtherProviders"]:
        kv_vals, section_settings = _get_config_secrets(cur_settings, section)
        kv_secrets_dict.update(kv_vals)
        ud_settings[section] = section_settings
    return ud_settings, kv_secrets_dict


def _show_settings(secrets, ud_settings):
    print("\nKV Secrets to update\n---------------------")
    pprint(secrets, indent=2)
    print("\nUpdated msticpyconfig\n---------------------")
    print(json.dumps(ud_settings, indent=2))


def _prompt_yn(mssg, confirm):
    if confirm:
        resp = input(mssg)  # nosec
    else:
        resp = "y"
    return resp.casefold().startswith("y")


def _add_secrets_to_vault(vault_name, secrets, confirm, **kwargs):
    print("Vault management requires authentication")
    kv_mgmt = BHKeyVaultMgmtClient(**kwargs)
    vault_uri = None
    try:
        vault_uri = kv_mgmt.get_vault_uri(vault_name)
        print(f"Vault {vault_name} found.")
    except CloudError:
        mssg = f"Vault {vault_name} not found. Create new vault (y/n)?"
        if _prompt_yn(mssg, confirm):
            print("Creating {vault_name}. Please wait...")
            new_vault = kv_mgmt.create_vault(vault_name=vault_name)
            vault_uri = new_vault.properties.vault_uri
            print("New vault {vault_name} created")
    if not vault_uri:
        print("Vault name was not created. Aborting.")
        return

    mssg = f"Add secrets to vault {vault_name} (y/n)?"
    print("Adding secrets to vault requires authentication")
    if _prompt_yn(mssg, confirm):
        kv_client = BHKeyVaultClient(vault_name=vault_name, **kwargs)
        for sec_name, sec_value in secrets.items():
            print(f"setting {sec_name}")
            kv_client.set_secret(secret_name=sec_name, value=sec_value)
        print("Done")
        print("Secrets in vault:\n", "\n".join(kv_client.secrets))


def _list_secrets(vault_name: str, confirm, **kwargs):
    mssg = "Show secret values (y/n)?"
    print(f"Secrets currently in vault {vault_name}")
    show_secrets = _prompt_yn(mssg, confirm)
    kv_client = BHKeyVaultClient(vault_name=vault_name, **kwargs)
    for sec_name in kv_client.secrets:
        print(f"Secret: {sec_name}", end=": ")
        if show_secrets:
            secret = kv_client.get_secret(secret_name=sec_name)
            print(secret.value)
        else:
            print("************")
        print("Done")


def _add_script_args(description):
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--path",
        "-p",
        default=".",
        required=False,
        help="Path to msticpyconfig.yaml. Defaults to using MSTICPYCONFIG env variable.",
    )
    parser.add_argument(
        "--vault",
        "-v",
        help="Vault name. Default taken from msticpyconfig.yaml")
    parser.add_argument(
        "--tenant",
        "-t",
        help="Tenant name or ID. Default taken from msticpyconfig.yaml",
    )
    parser.add_argument(
        "--sub",
        "-s",
        help="Subscription ID. Default taken from msticpyconfig.yaml")
    parser.add_argument(
        "--group",
        "-g",
        help=(
            "Resource Group name. Default taken from msticpyconfig.yaml"
            + "(only needed if creating new vault.)"
        ),
    )
    parser.add_argument(
        "--region",
        "-r",
        help=(
            "Azure region. Default taken from msticpyconfig.yaml"
            + "(only needed if creating new vault.)"
        ),
    )
    parser.add_argument(
        "--existing",
        "-e",
        action="store_true",
        default=False,
        help=("Use the named existing vault. Do not try to create."),
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        default=False,
        help=("View current secrets."),
    )
    parser.add_argument(
        "--show",
        action="store_true",
        default=False,
        help=("View changes that would be made without doing anything."),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help=("Print out more details."),
    )
    parser.add_argument(
        "--output",
        "-o",
        help=("Output file path to save updated msticpyconfig.yaml"))
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        default=False,
        help="Suppresses prompts for confirmation. Answers 'y' to all",
    )
    return parser


# pylint: disable=invalid-name
if __name__ == "__main__":
    arg_parser = _add_script_args(description=__doc__)
    args = arg_parser.parse_args()

    curr_settings, kv_settings = _read_config_settings(conf_file=args.path)
    vault = args.vault or kv_settings["vaultname"]
    kv_args = {
        "tenant_id": args.tenant or kv_settings["tenantid"],
        "subscription_id": args.sub or kv_settings["subscriptionid"],
        "resource_group": args.group or kv_settings["resourcegroup"],
        "azure_region": args.region or kv_settings["azureregion"],
        "settings": kv_settings,
    }

    prompt = not args.yes
    if args.list:
        _list_secrets(vault_name=vault, confirm=prompt, **kv_args)

    new_settings, kv_secrets = _transform_settings(curr_settings)
    if args.show or args.verbose:
        _show_settings(kv_secrets, new_settings)
        sys.exit(0)

    if not kv_secrets:
        print("No secrets found in config file. No action to take.")
        sys.exit(0)
    if not args.show:
        if not args.output:
            raise ValueError(
                "No output file specified. --output value is required.")
        _add_secrets_to_vault(
            vault_name=vault, secrets=kv_secrets, confirm=prompt, **kv_args
        )
        _write_config_settings(
            conf_file=args.output, conf_settings=new_settings, confirm=prompt
        )
