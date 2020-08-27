import logging
from followthemoney import model
from followthemoney.helpers import remove_checksums

from aleph.core import db, archive
from aleph.model import Mapping, Events
from aleph.index.entities import get_entity
from aleph.logic.aggregator import get_aggregator
from aleph.index.collections import delete_entities
from aleph.logic.collections import update_collection, index_aggregator
from aleph.logic.notifications import publish

log = logging.getLogger(__name__)


def _get_table_csv_link(table):
    proxy = model.get_proxy(table)
    csv_hash = proxy.first("csvHash")
    if csv_hash is None:
        raise RuntimeError("Source table doesn't have a CSV version")
    url = archive.generate_url(csv_hash)
    if url is None:
        local_path = archive.load_file(csv_hash)
        if local_path is not None:
            url = local_path.as_posix()
    if url is None:
        raise RuntimeError("Could not generate CSV URL for the table")
    return url


def mapping_origin(mapping_id):
    return "mapping:%s" % mapping_id


def map_to_aggregator(collection, mapping, aggregator):
    table = get_entity(mapping.table_id)
    if table is None:
        table = aggregator.get(mapping.table_id)
    if table is None:
        raise RuntimeError("Table cannot be found: %s" % mapping.table_id)
    config = {"csv_url": _get_table_csv_link(table), "entities": mapping.query}
    mapper = model.make_mapping(config, key_prefix=collection.foreign_id)
    origin = mapping_origin(mapping.id)
    aggregator.delete(origin=origin)
    writer = aggregator.bulk()
    idx = 0
    for idx, record in enumerate(mapper.source.records, 1):
        if idx > 0 and idx % 1000 == 0:
            log.info("[%s] Mapped %s rows ...", mapping.id, idx)
        for entity in mapper.map(record).values():
            entity.context = mapping.get_proxy_context()
            if entity.schema.is_a("Thing"):
                entity.add("proof", mapping.table_id)
            entity = collection.ns.apply(entity)
            entity = remove_checksums(entity)
            writer.put(entity, fragment=idx, origin=origin)
    writer.flush()
    log.info("[%s] Mapping done (%s rows)", mapping.id, idx)


def load_mapping(stage, collection, mapping_id, sync=False):
    """Flush and reload all entities generated by a mapping."""
    mapping = Mapping.by_id(mapping_id)
    if mapping is None:
        return log.error("Could not find mapping: %s", mapping_id)
    origin = mapping_origin(mapping.id)
    aggregator = get_aggregator(collection)
    aggregator.delete(origin=origin)
    delete_entities(collection.id, origin=origin, sync=True)
    if mapping.disabled:
        return log.info("Mapping is disabled: %s", mapping_id)
    publish(
        Events.LOAD_MAPPING,
        params={"collection": collection, "table": mapping.table_id},
        channels=[collection, mapping.role],
        actor_id=mapping.role_id,
    )
    try:
        map_to_aggregator(collection, mapping, aggregator)
        # FIXME: this doesn't re-overwrite entities....
        index_aggregator(collection, aggregator, sync=sync)
        mapping.set_status(status=Mapping.SUCCESS)
        db.session.commit()
    except Exception as exc:
        mapping.set_status(status=Mapping.FAILED, error=str(exc))
        db.session.commit()
        aggregator.delete(origin=origin)
    finally:
        aggregator.close()


def flush_mapping(stage, collection, mapping_id, sync=True):
    """Delete entities loaded by a mapping"""
    log.debug("Flushing entities for mapping: %s", mapping_id)
    origin = mapping_origin(mapping_id)
    aggregator = get_aggregator(collection)
    aggregator.delete(origin=origin)
    aggregator.close()
    delete_entities(collection.id, origin=origin, sync=sync)
    update_collection(collection, sync=sync)
