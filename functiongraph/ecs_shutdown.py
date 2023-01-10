# -*- coding:utf-8 -*-
# se necesita openstacksdk-1.0.6

import ssl
import time
import sys
from openstack import connection
from threading import Thread

ssl._create_default_https_context = ssl._create_unverified_context


def handler(event, context):
    projectId = context.getUserData('projectId', '').strip()
    region = context.getUserData('region', '').strip()
    domain = context.getUserData('domain', '').strip()
    ak = context.getAccessKey().strip()
    sk = context.getSecretKey().strip()
    whiteList = context.getUserData('whiteLists', '').strip().split(',')
    logger = context.getLogger()
    if not projectId:
        raise Exception("'projectId' not configured")

    if not region:
        raise Exception("'region' not configured")

    if not domain:
        logger.info(
            "domain not configured, use default value:myhuaweicloud.com")
        domain = 'myhuaweicloud.com'

    if not ak or not sk:
        ak = context.getUserData('ak', '').strip()
        sk = context.getUserData('sk', '').strip()
        if not ak or not sk:
            raise Exception("ak/sk empty")

    _shutdown_ecs(logger, projectId, domain, region, ak, sk, whiteList)


def _shutdown_ecs(logger, projectId, domain, region, ak, sk, whiteList):
    conn = connection.Connection(
        project_id=projectId, domain=domain, region=region, ak=ak, sk=sk)
    threads = []
    servers = conn.compute.servers()
    for server in servers:
        if server.name not in whiteList:
            logger.info(
                "skip stopping server '%s' for being in white lists." % (server.name))
            continue
        if "ACTIVE" != server.status:
            logger.info("skip stopping server '%s' for status not active(status: %s)." % (
                server.name, server.status))
            continue

        t = Thread(target=_stop_server, args=(conn, server, logger))
        t.start()
        threads.append(t)

    if not threads:
        logger.info("no servers to be stopped.")
        return

    logger.info("'%d' server(s) will be stopped.", len(threads))

    for t in threads:
        t.join()


def _stop_server(conn, server, logger):
    logger.info("stop server '%s'..." % (server.name))
    conn.compute.stop_server(server)

    cost = 0
    interval = 5
    wait = 600
    while cost < wait:
        temp = conn.compute.find_server(server.id)
        if temp and "SHUTOFF" != temp.status:
            time.sleep(interval)
            cost += interval
        else:
            break

    # conn.compute.wait_for_server(server, status="SHUTOFF", interval=5, wait=600)
    if cost >= wait:
        logger.warn("wait for stopping server '%s' timeout." % (server.name))
        return 2

    logger.info("stop server '%s' success." % (server.name))
    return 0
