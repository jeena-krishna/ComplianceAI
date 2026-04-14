import pytest
import shutil
import os
from complianceai.knowledge import LicenseRAG, get_rag_instance


@pytest.fixture
def temp_rag():
    temp_dir = "./test_chromadb_temp"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    rag = LicenseRAG(persist_directory=temp_dir)
    yield rag
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


def test_rag_initialization(temp_rag):
    assert temp_rag.collection.count() > 0


def test_search_licenses(temp_rag):
    results = temp_rag.search("permissive license")
    assert len(results) > 0
    assert results[0]["license_id"] in LICENSE_APPROVED


def test_get_license(temp_rag):
    license_data = temp_rag.get_license("MIT")
    assert license_data is not None
    assert license_data["license_id"] == "MIT"


def test_get_all_licenses(temp_rag):
    all_licenses = temp_rag.get_all_licenses()
    assert len(all_licenses) >= 12


def test_search_with_filter(temp_rag):
    results = temp_rag.search("copyleft GPL", n_results=5)
    assert len(results) > 0


def test_get_rag_instance_singleton():
    temp_dir = "./test_chromadb_singleton"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    
    rag1 = get_rag_instance(temp_dir)
    rag2 = get_rag_instance(temp_dir)
    
    assert rag1 is rag2
    
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


LICENSE_APPROVED = [
    "MIT", "Apache-2.0", "GPL-2.0", "GPL-3.0", "LGPL-2.1", 
    "LGPL-3.0", "AGPL-3.0", "BSD-2-Clause", "BSD-3-Clause",
    "MPL-2.0", "ISC", "Unlicense"
]