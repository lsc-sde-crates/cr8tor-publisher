#!/bin/sh
git config --global --add safe.directory /workspaces/cr8tor-publisher

mkdir -p ${TARGET_STORAGE_ACCOUNT_LSC_SDE_MNT_PATH}/staging
mkdir -p ${TARGET_STORAGE_ACCOUNT_LSC_SDE_MNT_PATH}/production
mkdir -p ${TARGET_STORAGE_ACCOUNT_NW_SDE_MNT_PATH}/staging
mkdir -p ${TARGET_STORAGE_ACCOUNT_NW_SDE_MNT_PATH}/production