import pytest
from analyst import IntelAnalyst

def test_person_entity_merging():
    analyst = IntelAnalyst()
    article = {
        'title': 'Joe Kent wins election',
        'description': 'Kent celebrates. Kent thanks supporters. Joe Kent is the winner.',
        'source': {'name': 'Test'},
        'publishedAt': '2026-04-12T10:00:00Z'
    }
    result = analyst.analyze_article(article)
    person_entities = [e[0] for e in result['entities'] if e[1] == 'PERSON']
    # Should only have one unique entity for Joe Kent
    assert person_entities.count('Joe Kent') == 1
    assert 'Kent' not in person_entities or person_entities.count('Kent') == 0

def test_org_gpe_normalization():
    analyst = IntelAnalyst()
    article = {
        'title': 'Oscars awarded in the U.S.',
        'description': 'The Oscars ceremony was held in the U.S. The United States hosted the Oscars.',
        'source': {'name': 'Test'},
        'publishedAt': '2026-04-12T10:00:00Z'
    }
    result = analyst.analyze_article(article)
    org_entities = [e[0] for e in result['entities'] if e[1] == 'ORG']
    gpe_entities = [e[0] for e in result['entities'] if e[1] == 'GPE']
    # Oscars should be singular and U.S. normalized
    assert 'Oscar' in org_entities
    assert 'Oscars' not in org_entities
    assert 'United States' in gpe_entities
    assert 'U.S.' not in gpe_entities

if __name__ == "__main__":
    test_person_entity_merging()
    test_org_gpe_normalization()
    print("Entity normalization tests passed.")
