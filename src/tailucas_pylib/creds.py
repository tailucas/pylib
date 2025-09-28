import asyncio
import logging

from logging import Logger
from os import getenv, path
from typing import List

APP_NAME = getenv("APP_NAME", "test")
log: Logger = logging.getLogger(APP_NAME)


CONTAINER_SECRETS_PATH = "/run/secrets"


def get_secret_or_env(var_name: str) -> str:
    if not path.exists(CONTAINER_SECRETS_PATH):
        var_val = getenv(var_name)
        if not var_val:
            raise AssertionError(f"Environment variable {var_name} is unset.")
        else:
            return var_val
    secret_file = f"{CONTAINER_SECRETS_PATH}/{var_name.lower()}"
    with open(secret_file, "r") as f:
        return f.read()


class Creds:
    def __init__(self):
        self.op_vault: str = get_secret_or_env("OP_VAULT")
        self.op_connect_host: str = getenv("OP_CONNECT_HOST")  # type: ignore
        creds_use_connect_client = getenv(
            "CREDS_USE_CONNECT_CLIENT", "true"
        ).lower() in (
            "true",
            "1",
            "t",
        )
        creds_use_service_client = getenv(
            "CREDS_USE_SERVICE_CLIENT", "true"
        ).lower() in (
            "true",
            "1",
            "t",
        )
        self.connect_client = None  # type: ignore
        self.service_client = None  # type: ignore
        if self.op_vault is None:
            raise AssertionError("Environment variable self.op_vault is unset.")
        if creds_use_connect_client and self.op_connect_host:
            from onepasswordconnectsdk.client import Client as ConnectClient
            from onepasswordconnectsdk.client import new_client

            self.connect_client: ConnectClient = new_client(
                url=self.op_connect_host,
                token=get_secret_or_env("OP_CONNECT_TOKEN"),
                is_async=False,
            )  # type: ignore
        if creds_use_service_client:
            from onepassword import Client as ServiceClient

            self.service_client: ServiceClient = asyncio.run(
                ServiceClient.authenticate(
                    auth=get_secret_or_env("OP_SERVICE_ACCOUNT_TOKEN"),
                    integration_name=APP_NAME,
                    integration_version="v1.0.0",
                )
            )
        if not self.connect_client and not self.service_client:
            raise AssertionError(
                "No 1Password client created. Set OP_CONNECT_TOKEN or OP_SERVICE_ACCOUNT_TOKEN or define container secrets in {CONTAINER_SECRET_PATH}."
            )

    def validate_creds(self):
        if self.connect_client:
            from onepasswordconnectsdk.models import Vault

            creds_vaults: List[Vault] = self.connect_client.get_vaults()
            vault_found = False
            for vault in creds_vaults:
                log.info(
                    f"Credential vault on 1Password server {self.op_connect_host} {vault.name} ({vault.id}) contains {vault.items} credentials."
                )
                if self.op_vault == vault.id:
                    vault_found = True
            if len(creds_vaults) == 1:
                self.op_vault = creds_vaults[0].id  # type: ignore
                vault_found = True
            if not vault_found:
                raise Exception(
                    f"No vault matching ID {self.op_vault} found on 1Password connect server {self.op_connect_host}. See https://github.com/1Password/connect-sdk-python/"
                )
        if self.service_client:
            from onepassword.types import VaultOverview

            vault_found = False
            vaults: List[VaultOverview] = asyncio.run(self.service_client.vaults.list())
            for vault in vaults:
                log.info(
                    f"Credential vault on 1Password service {vault.title} ({vault.id})."
                )
                if self.op_vault == vault.id:
                    vault_found = True
            if len(vaults) == 1:
                self.op_vault = vaults[0].id
                vault_found = True
            if not vault_found:
                raise Exception(
                    f"No vault matching ID {self.op_vault} found in 1Password service. See https://github.com/1Password/onepassword-sdk-python/"
                )

    def get_creds(self, creds_path) -> str:
        if self.connect_client:
            from onepasswordconnectsdk.models import Item, SummaryItem, Field, Section
            from onepasswordconnectsdk.errors import FailedToRetrieveItemException

            try:
                creds_path_parts = creds_path.split("/")
                item: Item = self.connect_client.get_item(
                    creds_path_parts[0], self.op_vault
                )  # type: ignore
                if len(creds_path_parts) == 1:
                    item_fields: List[Field] = item.fields  # type: ignore
                    if len(item_fields) == 1:
                        return item_fields[0].value  # type: ignore
                    else:
                        field_titles = []
                        for item_field in item_fields:
                            field_titles.append(item_field.label)
                        raise AssertionError(
                            f"Ambiguous field specification in {creds_path}. Available: {field_titles!s}"
                        )
                elif len(creds_path_parts) == 2:
                    field_labels = dict()
                    item_fields: List[Field] = item.fields  # type: ignore
                    for item_field in item_fields:
                        if item_field.label not in field_labels:
                            field_labels[item_field.label] = 1
                        else:
                            field_labels[item_field.label] += 1
                        if item_field.label == creds_path_parts[1]:
                            return item_field.value  # type: ignore
                    raise AssertionError(
                        f"Ambiguous field specification in {creds_path}. Available: {field_labels!s}"
                    )
                elif len(creds_path_parts) == 3:
                    item_sections: List[Section] = item.sections  # type: ignore
                    section_id = None
                    for item_section in item_sections:
                        if item_section.label == creds_path_parts[1]:
                            section_id = item_section.id
                            break
                    if section_id is None:
                        raise AssertionError(
                            f"Section {creds_path_parts[1]} not found in item {creds_path} in vault {self.op_vault} on 1Password connect server {self.op_connect_host}."
                        )
                    item_fields: List[Field] = item.fields  # type: ignore
                    field_labels = dict()
                    for item_field in item_fields:
                        if item_field.label not in field_labels:
                            field_labels[item_field.label] = 1
                        else:
                            field_labels[item_field.label] += 1
                        if item_field.section is None:
                            continue
                        if (
                            item_field.section.id == section_id
                            and item_field.label == creds_path_parts[2]
                        ):
                            return item_field.value  # type: ignore
                    raise AssertionError(
                        f"Ambiguous field specification in {creds_path}. Available: {field_labels!s}"
                    )
            except FailedToRetrieveItemException as e:
                items_summary: List[SummaryItem] = self.connect_client.get_items(
                    self.op_vault
                )  # type: ignore
                item_titles = []
                for item_summary in items_summary:
                    item_titles.append(item_summary.title)
                raise AssertionError(
                    f"Failed to retrieve item {creds_path} from vault {self.op_vault} on 1Password connect server {self.op_connect_host}: {e!s} (available: {item_titles!s})"
                )
        elif self.service_client:
            return asyncio.run(
                self.service_client.secrets.resolve(
                    f"op://{self.op_vault}/{creds_path}"
                )
            )
        else:
            raise AssertionError(f"No credential client available for {creds_path}.")
        raise AssertionError(f"No credential retrieved for {creds_path}")

    def get_fields_from_sections(
        self, item_title, section_names: List[str]
    ) -> dict[str, str]:
        key_value_pairs = dict()
        if self.connect_client:
            from onepasswordconnectsdk.models import Item, Field, Section

            item: Item = self.connect_client.get_item(item_title, self.op_vault)  # type: ignore
            item_sections: List[Section] = item.sections  # type: ignore
            if item_sections is None:
                raise AssertionError(
                    f"No sections found in item {item_title} in vault {self.op_vault} on 1Password connect server {self.op_connect_host}."
                )
            section_ids = []
            for item_section in item_sections:
                if item_section.label in section_names:  # type: ignore
                    section_ids.append(item_section.id)
            item_fields: List[Field] = item.fields  # type: ignore
            for item_field in item_fields:  # type: ignore
                if item_field.section is None:  # type: ignore
                    continue
                if item_field.section.id in section_ids:  # type: ignore
                    key_value_pairs[item_field.label] = item_field.value  # type: ignore
            return key_value_pairs
        elif self.service_client:
            from onepassword.types import ItemOverview, Item, ItemSection, ItemField

            creds_items: List[ItemOverview] = asyncio.run(
                self.service_client.items.list(self.op_vault)
            )  # type: ignore
            for cred_item in creds_items:
                item: Item = self.service_client.items.get(self.op_vault, cred_item.id)  # type: ignore
                if item.title != item_title:
                    continue
                op_sections = dict()
                if len(item.sections) > 0:
                    item_sections: List[ItemSection] = item.sections
                    for item_section in item_sections:
                        op_sections[item_section.id] = item_section.title
                item_field: ItemField = None  # type: ignore
                for item_field in item.fields:
                    if item_field.section_id is None:
                        continue
                    op_section_title = op_sections[item_field.section_id]
                    if op_section_title in section_names:
                        if item_field.title in key_value_pairs:
                            raise AssertionError(
                                f"{item_field.title} already present, check duplicates across sections in {item.title}."
                            )
                        key_value_pairs[item_field.title] = item_field.value
            return key_value_pairs
        else:
            raise AssertionError(f"No credential client available for {item_title}.")
