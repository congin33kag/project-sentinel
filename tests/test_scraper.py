# Location: /Vibe Coding 101/tests/test_scraper.py

import pytest
from app.services.scraper_service import parse_name_and_aliases

def test_parse_name_and_aliases_basic():
    """Tests basic name and alias splitting."""
    name, aliases = parse_name_and_aliases("Jaish-E-Mohammed/Tahreik-E-Furqan")
    assert name == "Jaish-E-Mohammed"
    assert set(aliases) == {"Tahreik-E-Furqan"}

def test_parse_name_with_boilerplate():
    """Tests that boilerplate is correctly removed before parsing."""
    name, aliases = parse_name_and_aliases(
        "Lashkar-E-Taiba/Pasban-E-Ahle Hadis and all its manifestations and front organizations."
    )
    assert name == "Lashkar-E-Taiba"
    assert set(aliases) == {"Pasban-E-Ahle Hadis"}

def test_parse_name_with_parentheses():
    """Tests alias extraction from parentheses."""
    name, aliases = parse_name_and_aliases("Students Islamic Movement of India (SIMI)")
    assert name == "Students Islamic Movement of India"
    assert set(aliases) == {"SIMI"}

def test_whitespace_normalization():
    """Tests that extra whitespace is handled correctly."""
    name, aliases = parse_name_and_aliases(
        "Al-Qaeda   and   all  its  manifestations"
    )
    assert name == "Al-Qaeda"
    assert not aliases

def test_multiple_aliases_and_delimiters():
    """Tests handling of multiple different separators."""
    name, aliases = parse_name_and_aliases("Al-Qaeda/AQ (The Base; The Foundation)")
    expected_aliases = {"AQ", "The Base", "The Foundation"}
    assert name == "Al-Qaeda"
    assert set(aliases) == expected_aliases

def test_case_insensitive_deduplication():
    """Tests that duplicates with different casing are handled."""
    name, aliases = parse_name_and_aliases("ISIS/isis (ISIS)")
    assert name == "ISIS"
    assert set(aliases) == set()  # All variations deduplicated to primary

def test_short_aliases_are_kept():
    """Ensures important short aliases like 'AQ' are not filtered out."""
    name, aliases = parse_name_and_aliases("Al-Qaeda/AQ")
    assert name == "Al-Qaeda"
    assert set(aliases) == {"AQ"}

def test_no_aliases():
    """Tests a name with no aliases."""
    name, aliases = parse_name_and_aliases("Babbar Khalsa International")
    assert name == "Babbar Khalsa International"
    assert not aliases
