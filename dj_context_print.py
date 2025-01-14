# token_analyzer.py
# Copyright (c) 2024 Giuseppe Birardi
# Licensed under the MIT License - see LICENSE file for details

import os
import time
import json
import ast
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class FileInfo:
    path: str
    last_modified: float
    size: int
    token_estimate: int
    content: str = None


class TokenAwareAnalyzer:
    # Token limit and conversion settings
    MAX_TOKENS = 50_000
    CHARS_PER_TOKEN = 4  # Approssimazione media
    MAX_CHAR_SIZE = MAX_TOKENS * CHARS_PER_TOKEN

    # Directories da escludere
    EXCLUDED_DIRECTORIES: Set[str] = {
        '.idea/', '.git', 'venv', '.venv', 'env',
        '__pycache__', 'node_modules', 'media',
        'static', 'migrations'
    }

    # Pattern di file Django da includere
    DJANGO_PATTERNS: Dict[str, List[str]] = {
        'models': ['models.py'],
        'views': ['views.py', 'viewsets.py', 'apis.py'],
        'urls': ['urls.py'],
        'forms': ['forms.py'],
        'serializers': ['serializers.py'],
        'templates': ['.html'],
        'static': ['.js', '.css']
    }

    def __init__(self, project_root: str = '.'):
        self.project_root = project_root
        self.output_dir = 'print_codebase'
        self.selected_files = []
        os.makedirs(self.output_dir, exist_ok=True)

    def find_app_directory(self, file_path: str) -> str:
        """Identifica la directory dell'app Django dal path del file."""
        parts = file_path.split(os.sep)
        for i in range(len(parts) - 1, -1, -1):
            if any(f == parts[i] for f in ['views', 'models', 'forms', 'urls']):
                return os.path.join(*parts[:i])
        return os.path.dirname(file_path)

    def get_correlated_files(self, file_info: FileInfo, all_files: List[FileInfo]) -> Set[str]:
        """Trova i file correlati basandosi sul contesto Django."""
        correlated = set()
        app_dir = self.find_app_directory(file_info.path)

        # Se è una view, cerca models, forms, urls e templates correlati
        if 'views.py' in file_info.path:
            view_content = file_info.content

            # Estrai i nomi delle classi e funzioni dalla view
            try:
                tree = ast.parse(view_content)
                view_names = {
                    node.name.lower()
                    for node in ast.walk(tree)
                    if isinstance(node, (ast.ClassDef, ast.FunctionDef))
                }
            except:
                view_names = set()

            for other_file in all_files:
                other_path = other_file.path

                # Stesso modulo/app
                if app_dir in other_path:
                    if any(x in other_path for x in ['models.py', 'forms.py', 'urls.py']):
                        correlated.add(other_path)

                # Template correlati
                if other_path.endswith('.html'):
                    if any(name in other_path.lower() for name in view_names):
                        correlated.add(other_path)

        # Se è un model, cerca views e forms correlati
        elif 'models.py' in file_info.path:
            model_name = os.path.splitext(os.path.basename(file_info.path))[0]
            for other_file in all_files:
                if app_dir in other_file.path:
                    if any(x in other_file.path for x in ['views.py', 'forms.py']):
                        # Verifica se il model è importato
                        if model_name in other_file.content:
                            correlated.add(other_file.path)

        # Se è un template, cerca le views correlate
        elif file_info.path.endswith('.html'):
            template_name = os.path.splitext(os.path.basename(file_info.path))[0]
            for other_file in all_files:
                if 'views.py' in other_file.path:
                    if template_name in other_file.content:
                        correlated.add(other_file.path)
                        # Aggiungi anche i models e forms usati in questa view
                        app_files = [f for f in all_files if app_dir in f.path]
                        for app_file in app_files:
                            if any(x in app_file.path for x in ['models.py', 'forms.py']):
                                correlated.add(app_file.path)

        return correlated

    def estimate_tokens(self, content: str) -> int:
        """Stima approssimativa del numero di token in un contenuto."""
        return len(content) // self.CHARS_PER_TOKEN

    def get_file_info(self, file_path: str) -> FileInfo:
        """Ottiene informazioni dettagliate su un file, inclusa la stima dei token."""
        abs_path = os.path.join(self.project_root, file_path)
        with open(abs_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return FileInfo(
                path=file_path,
                last_modified=os.path.getmtime(abs_path),
                size=len(content),
                token_estimate=self.estimate_tokens(content),
                content=content
            )

    def get_project_files(self) -> List[FileInfo]:
        """Raccoglie tutti i file rilevanti con le loro informazioni."""
        files = []
        for root, dirs, filenames in os.walk(self.project_root):
            dirs[:] = [d for d in dirs if d not in self.EXCLUDED_DIRECTORIES]

            for file in filenames:
                # Verifica sia per file Python che per template/static
                is_django_file = any(
                    file.endswith(pat.replace('*.py', '.py'))
                    or file.endswith(pat)
                    for patterns in self.DJANGO_PATTERNS.values()
                    for pat in patterns
                )

                # Verifica specifica per i template
                is_template = file.endswith('.html') and ('templates' in root or '/templates/' in root)

                if is_django_file or is_template:
                    rel_path = os.path.relpath(os.path.join(root, file), self.project_root)
                    try:
                        file_info = self.get_file_info(rel_path)
                        files.append(file_info)
                    except Exception as e:
                        print(f"Errore nella lettura del file {rel_path}: {e}")

        return sorted(files, key=lambda x: x.last_modified, reverse=True)

    def calculate_file_score(self, file_info: FileInfo, all_files: List[FileInfo]) -> float:
        """Calcola un punteggio di priorità per ogni file, considerando le correlazioni."""
        score = 0.0

        # Punteggio base per tipo di file
        file_priorities = {
            'settings.py': 100,
            'urls.py': 90,
            'models.py': 80,
            'views.py': 70,
            'forms.py': 60,
            'serializers.py': 50,
            'tests.py': 30
        }

        filename = os.path.basename(file_info.path)

        # Controlla se il file è stato modificato di recente
        hours_since_modification = (time.time() - file_info.last_modified) / 3600
        is_recently_modified = hours_since_modification < 24  # Modificato nelle ultime 24 ore

        # Se il file è stato modificato di recente, dai priorità ai file correlati
        if is_recently_modified:
            correlated_files = self.get_correlated_files(file_info, all_files)
            if file_info.path in correlated_files:
                score += 150  # Alta priorità per i file correlati a modifiche recenti

        # Calcolo punteggio base per tipo di file
        if filename.endswith('.html'):
            if 'base.html' in filename:
                score += 85
            elif '/templates/' in file_info.path:
                score += 65
        elif filename.endswith('.py'):
            score += file_priorities.get(filename, 40)
        elif filename.endswith(('.js', '.css')):
            score += 35

        # Bonus/Penalità aggiuntive
        recency_score = max(0, 100 - (hours_since_modification / 24) * 10)
        score += recency_score

        size_penalty = max(0, (file_info.token_estimate / 1000) * 5)
        score -= size_penalty

        return score

    def select_files_within_limit(self, files: List[FileInfo]) -> List[FileInfo]:
        """Seleziona i file da includere, dando priorità ai file correlati."""
        self.selected_files = []
        total_tokens = 0

        # Prima passa: trova i file modificati di recente e i loro correlati
        recent_files = set()
        correlated_to_recent = set()

        for file in files:
            hours_since_modification = (time.time() - file.last_modified) / 3600
            if hours_since_modification < 24:  # Modificato nelle ultime 24 ore
                recent_files.add(file.path)
                correlated = self.get_correlated_files(file, files)
                correlated_to_recent.update(correlated)

        # Calcola i punteggi e ordina i file
        scored_files = []
        for file in files:
            base_score = self.calculate_file_score(file, files)
            if file.path in recent_files:
                base_score += 200  # Bonus per file modificati di recente
            elif file.path in correlated_to_recent:
                base_score += 150  # Bonus per file correlati a modifiche recenti
            scored_files.append((file, base_score))

        scored_files.sort(key=lambda x: x[1], reverse=True)

        # Seleziona i file rispettando il limite di token
        for file, score in scored_files:
            if total_tokens + file.token_estimate <= self.MAX_TOKENS:
                self.selected_files.append(file)
                total_tokens += file.token_estimate

        return self.selected_files

    def generate_report(self):
        """Genera un unico report completo che include sia la struttura che i contenuti."""
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(self.output_dir, f'codebase_report.txt')

        all_files = self.get_project_files()
        selected_files = self.select_files_within_limit(all_files)

        # Prepara la struttura del progetto
        project_structure = {
            'timestamp': timestamp,
            'project_root': self.project_root,
            'files_by_type': {
                'models': [],
                'views': [],
                'templates': [],
                'forms': [],
                'urls': [],
                'static': [],
                'other': []
            }
        }

        # Categorizza i file
        for file in all_files:
            file_info = {
                'path': file.path,
            }

            filename = os.path.basename(file.path)
            if 'models.py' in filename:
                project_structure['files_by_type']['models'].append(file_info)
            elif 'views.py' in filename:
                project_structure['files_by_type']['views'].append(file_info)
            elif filename.endswith('.html'):
                project_structure['files_by_type']['templates'].append(file_info)
            elif 'forms.py' in filename:
                project_structure['files_by_type']['forms'].append(file_info)
            elif 'urls.py' in filename:
                project_structure['files_by_type']['urls'].append(file_info)
            elif filename.endswith(('.js', '.css')):
                project_structure['files_by_type']['static'].append(file_info)
            else:
                project_structure['files_by_type']['other'].append(file_info)

        with open(output_file, 'w', encoding='utf-8') as f:
            # 1. Header e statistiche
            f.write("=== DJANGO PROJECT ANALYSIS ===\n")
            f.write(f"Generated: {timestamp}\n")
            f.write("=" * 40 + "\n\n")

            total_tokens = sum(file.token_estimate for file in selected_files)
            f.write(f"STATISTICHE GENERALI:\n")
            f.write(f"- Files inclusi: {len(selected_files)}\n")
            f.write(f"- Token totali: {total_tokens:,} / {self.MAX_TOKENS:,}\n")
            f.write(f"- Utilizzo token: {(total_tokens / self.MAX_TOKENS) * 100:.1f}%\n\n")

            # 2. Struttura del progetto in formato JSON
            f.write("=== STRUTTURA DEL PROGETTO ===\n")
            f.write("```json\n")
            f.write(json.dumps(project_structure, indent=2))
            f.write("\n```\n\n")

            # 3. Contenuto dei file
            f.write("=== CONTENUTO DEI FILE ===\n")
            for file_info in selected_files:
                f.write(f"\n--- {file_info.path} ---\n")
                f.write(f"Ultima modifica: {datetime.fromtimestamp(file_info.last_modified)}\n")
                f.write("```\n")  # Inizio del blocco di codice
                f.write(file_info.content)
                f.write("\n```\n")  # Fine del blocco di codice
                f.write("-" * 40 + "\n")

            # 4. Files esclusi
            excluded_files = [f for f in all_files if f not in selected_files]
            if excluded_files:
                f.write("\n=== FILES ESCLUSI ===\n")
                for file in excluded_files:
                    f.write(f"- {file.path} ({file.token_estimate:,} token stimati)\n")

    def analyze_directory(self, directory_path: str):
        """Analizza una directory e salva l'output in un file."""
        if not os.path.exists(directory_path):
            print(f"Error: Directory '{directory_path}' non trovata.")
            return

        timestamp = time.strftime('%Y%m%d_%H%M%S')
        parent_dir_name = os.path.basename(os.path.dirname(directory_path))
        dir_name = os.path.basename(directory_path)
        output_file = os.path.join(self.output_dir, f'directory_analysis_{parent_dir_name}_{dir_name}.txt')

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"\nAnalisi della directory: {directory_path}\n")
            f.write(f"{timestamp}\n")
            f.write("=" * 50 + "\n")
            f.write("\nSTRUTTURA DIRECTORY:\n")
            f.write("=" * 50 + "\n")

            # Prima scrivi la struttura
            for root, dirs, files in os.walk(directory_path):
                dirs[:] = [d for d in dirs if d not in self.EXCLUDED_DIRECTORIES]

                level = root[len(directory_path):].count(os.sep)
                indent = '  ' * level

                f.write(f"{indent}{os.path.basename(root)}/\n")

                subindent = '  ' * (level + 1)
                for file in files:
                    file_path = os.path.join(root, file)
                    size = os.path.getsize(file_path)
                    modified = datetime.fromtimestamp(os.path.getmtime(file_path))

                    if size < 1024:
                        size_str = f"{size} B"
                    elif size < 1024 * 1024:
                        size_str = f"{size / 1024:.1f} KB"
                    else:
                        size_str = f"{size / (1024 * 1024):.1f} MB"

                    f.write(f"{subindent}{file} ({size_str}) - Modificato: {modified.strftime('%Y-%m-%d %H:%M:%S')}\n")

            # Poi scrivi i contenuti
            f.write("\nCONTENUTI DEI FILE:\n")
            f.write("=" * 50 + "\n")

            for root, dirs, files in os.walk(directory_path):
                dirs[:] = [d for d in dirs if d not in self.EXCLUDED_DIRECTORIES]

                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, directory_path)

                    try:
                        with open(file_path, 'r', encoding='utf-8') as source:
                            content = source.read()
                            f.write(f"\n--- {rel_path} ---\n")
                            f.write("```\n")
                            f.write(content)
                            f.write("\n```\n")
                            f.write("-" * 40 + "\n")
                    except Exception as e:
                        f.write(f"\nError reading {rel_path}: {e}\n")

        print(f"Analisi completata. Output salvato in: {output_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Django Project Analyzer')
    parser.add_argument('--dir', '-d', type=str, help='Directory da analizzare')
    parser.add_argument('--report', '-r', action='store_true', help='Genera un report completo')

    args = parser.parse_args()
    analyzer = TokenAwareAnalyzer()

    if args.dir:
        analyzer.analyze_directory(args.dir)
    if args.report:
        print("\nGenerazione report completo...")
        analyzer.generate_report()
    if not args.dir and not args.report:
        print("Uso: python token_analyzer.py [-d DIRECTORY] [-r]")
        print("Esempio:\n  python token_analyzer.py -d ./myapp -r")