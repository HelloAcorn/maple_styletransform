"""
캐릭터 카테고리 매핑 설정
각 캐릭터의 특성(무기 유무, 탑승물 등)에 따라 적합한 비디오 프롬프트 카테고리를 정의합니다.
"""

from typing import Dict, List
from enum import Enum


class CharacterCategory(Enum):
    """캐릭터 카테고리"""
    NO_WEAPON = "no_weapon"        # 무기가 없는 캐릭터
    WITH_WEAPON = "with_weapon"    # 무기가 있는 캐릭터
    WITH_JAGUAR = "with_jaguar"    # 재규어를 타는 캐릭터
    WITH_MACHINE = "with_machine"  # 기계를 타는 캐릭터


# 캐릭터 이름 → 카테고리 매핑
CHARACTER_CATEGORY_MAPPING: Dict[str, CharacterCategory] = {
    # 무기가 없는 캐릭터
    "핑크빈": CharacterCategory.NO_WEAPON,
    "예티": CharacterCategory.NO_WEAPON,
    
    # 무기가 있는 캐릭터
    "데몬슬레이어": CharacterCategory.WITH_WEAPON,
    "메르세데스": CharacterCategory.WITH_WEAPON,
    "아크메이지": CharacterCategory.WITH_WEAPON,
    "엔젤릭버스터": CharacterCategory.WITH_WEAPON,
    "캐논슈터": CharacterCategory.WITH_WEAPON,
    "캡틴": CharacterCategory.WITH_WEAPON,
    "팬텀": CharacterCategory.WITH_WEAPON,
    "히어로": CharacterCategory.WITH_WEAPON,
    "호영": CharacterCategory.WITH_WEAPON,
    
    # 재규어를 타는 캐릭터
    "와일드헌터": CharacterCategory.WITH_JAGUAR,
    
    # 기계를 타는 캐릭터
    "메카닉": CharacterCategory.WITH_MACHINE,
}


def get_character_category(character_name: str) -> CharacterCategory:
    """
    캐릭터 이름으로 카테고리 반환
    
    Args:
        character_name: 캐릭터 이름
        
    Returns:
        CharacterCategory: 해당 캐릭터의 카테고리
        
    Raises:
        ValueError: 매핑되지 않은 캐릭터인 경우
    """
    if character_name in CHARACTER_CATEGORY_MAPPING:
        return CHARACTER_CATEGORY_MAPPING[character_name]
    
    # 기본값: 무기가 있는 캐릭터로 처리
    return CharacterCategory.WITH_WEAPON


def get_video_prompt_directory(character_name: str) -> str:
    """
    캐릭터 이름으로 비디오 프롬프트 디렉토리 경로 반환
    
    Args:
        character_name: 캐릭터 이름
        
    Returns:
        str: 프롬프트 디렉토리 경로 (상대 경로)
    """
    category = get_character_category(character_name)
    return f"app/prompt/video/{category.value}"


def get_characters_by_category(category: CharacterCategory) -> List[str]:
    """
    카테고리별 캐릭터 목록 반환
    
    Args:
        category: 캐릭터 카테고리
        
    Returns:
        List[str]: 해당 카테고리의 캐릭터 이름 목록
    """
    return [
        char_name for char_name, char_category in CHARACTER_CATEGORY_MAPPING.items()
        if char_category == category
    ]


def get_all_categories() -> List[CharacterCategory]:
    """모든 카테고리 목록 반환"""
    return list(CharacterCategory)


def get_category_description(category: CharacterCategory) -> str:
    """카테고리 설명 반환"""
    descriptions = {
        CharacterCategory.NO_WEAPON: "(핑크빈, 예티)",
        CharacterCategory.WITH_WEAPON: "(데몬슬레이어, 메르세데스, 아크메이지, 엔젤릭버스터, 캐논슈터, 캡틴, 팬텀, 히어로, 호영)",
        CharacterCategory.WITH_JAGUAR: "(와일드헌터)",
        CharacterCategory.WITH_MACHINE: "(메카닉)"
    }
    return descriptions.get(category, "알 수 없는 카테고리")


if __name__ == "__main__":
    # 테스트 및 확인용
    print("=== 캐릭터 카테고리 매핑 ===\n")
    
    for category in get_all_categories():
        print(f"📁 {category.value}: {get_category_description(category)}")
        characters = get_characters_by_category(category)
        for char in characters:
            print(f"   - {char}")
        print()
    
    # 샘플 테스트
    print("\n=== 샘플 테스트 ===")
    test_characters = ["핑크빈", "데몬슬레이어", "와일드헌터", "메카닉"]
    for char in test_characters:
        category = get_character_category(char)
        directory = get_video_prompt_directory(char)
        print(f"{char} → {category.value} → {directory}")

