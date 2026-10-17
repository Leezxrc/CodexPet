import ast
from pathlib import Path
import re
from string import Formatter
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from codexpet.i18n import CATALOG, Translator
from codexpet.quota import Window, reset_text

CJK = re.compile(r'[\u4e00-\u9fff]')


class TranslationTests(unittest.TestCase):
    def test_catalog_has_matching_placeholders_and_no_untranslated_text(self):
        fields = lambda text: {f for _, f, _, _ in Formatter().parse(text) if f}
        for source, translations in CATALOG.items():
            for language in ('en', 'tr'):
                with self.subTest(source=source, language=language):
                    self.assertEqual(fields(source), fields(translations[language]))
                    self.assertFalse(CJK.search(translations[language]))

    def test_all_static_backend_errors_and_ui_copy_are_covered(self):
        root = Path(__file__).resolve().parents[1] / 'src' / 'codexpet'
        # These are fragments of composed messages or intentionally native names.
        fragments = {'码伴', ' · 上次', '；旧数据可能属于此前登录账号。', '语言 / Language / Dil'}
        for filename in ('client.py', 'connection.py', 'connection_dialog.py', 'app.py', 'quota.py', 'appearance.py'):
            tree = ast.parse((root / filename).read_text(encoding='utf-8'))
            fstring_parts = {id(part) for node in ast.walk(tree) if isinstance(node, ast.JoinedStr) for part in node.values}
            for node in ast.walk(tree):
                if not isinstance(node, ast.Constant) or not isinstance(node.value, str) or id(node) in fstring_parts:
                    continue
                text = node.value
                if text in fragments or not CJK.search(text):
                    continue
                for language in ('en', 'tr'):
                    with self.subTest(file=filename, line=node.lineno, language=language):
                        self.assertFalse(CJK.search(Translator(language)(text)), text)

    def test_dynamic_progress_quota_and_composed_messages(self):
        for language in ('en', 'tr'):
            translate = Translator(language)
            samples = [Window(25, 300, 800000), Window(25, 10080, 800000), Window(25, 2880, 800000), Window(25, 45, 800000)]
            for window in samples:
                self.assertFalse(CJK.search(translate(window.label)))
                for now in (1, 799000, 799950, 800000):
                    self.assertFalse(CJK.search(translate(reset_text(window, now))))
            for text in ('正在下载 codex-app-server：123 MB（首次连接需要）', '正在校验并准备 codex…',
                         '重置卡 · 上次', '5 小时额度 · 10/18 13:00（本机时间）',
                         '读取额度超时，稍后会自动重试；旧数据可能属于此前登录账号。',
                         'Plus · 上次更新 12:30:15\n每 2 分钟自动刷新 · 右键可调整桌宠',
                         'CodexPet · 码伴\n5 小时额度：剩余 66%\n重置卡：2 张\n额外积分：未提供'):
                self.assertFalse(CJK.search(translate(text)), text)

    def test_turkish_numbers_and_invalid_language_fallback(self):
        self.assertEqual(Translator('tr').number('1,234.50'), '1.234,50')
        self.assertEqual(Translator('en').number('1,234.50'), '1,234.50')
        self.assertEqual(Translator(['tr']).language, 'zh-CN')
        self.assertEqual(Translator('invalid')('重置卡'), '重置卡')


if __name__ == '__main__':
    unittest.main()
