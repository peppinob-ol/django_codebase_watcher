# watch_analyzer.py
# Copyright (c) 2024 Giuseppe Birardi
# Licensed under the MIT License - see LICENSE file for details
import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dj_context_print import TokenAwareAnalyzer


class DjangoWatcher:
    def __init__(self, directory_to_watch='./', cooldown=5, included_dirs=None):
        self.DIRECTORY_TO_WATCH = directory_to_watch
        self.cooldown = cooldown  # Tempo minimo tra le analisi
        self.included_dirs = included_dirs or []  # Lista delle directory da monitorare
        self.observer = Observer()
        self.last_run = 0

    def run(self):
        event_handler = DjangoHandler(self.cooldown, self.included_dirs)
        self.observer.schedule(event_handler, self.DIRECTORY_TO_WATCH, recursive=True)
        self.observer.start()
        print(f"Monitoraggio avviato nella directory: {self.DIRECTORY_TO_WATCH}")
        if self.included_dirs:
            print("Directory monitorate:")
            for dir_path in self.included_dirs:
                print(f"- {dir_path}")
        else:
            print("Monitoraggio attivo su tutte le directory")
        print("Premi Ctrl+C per terminare...")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nArresto del monitoraggio...")
            self.observer.stop()
        self.observer.join()


class DjangoHandler(FileSystemEventHandler):
    def __init__(self, cooldown, included_dirs=None):
        self.cooldown = cooldown
        self.last_run = 0
        self.relevant_extensions = {'.py', '.html', '.js', '.css'}
        self.included_dirs = [os.path.normpath(d) for d in (included_dirs or [])]
        self.analyzer = TokenAwareAnalyzer(included_dirs=self.included_dirs)

    def is_path_included(self, path):
        if not self.included_dirs:
            return True

        normalized_path = os.path.normpath(path)
        return any(
            normalized_path.startswith(os.path.normpath(included_dir))
            for included_dir in self.included_dirs
        )

    def on_modified(self, event):
        # Verifica se il file è rilevante
        if event.is_directory:
            return

        # Verifica se il path è nelle directory incluse
        if not self.is_path_included(event.src_path):
            return

        file_ext = os.path.splitext(event.src_path)[1]
        if file_ext not in self.relevant_extensions:
            return

        # Controlla il cooldown
        current_time = time.time()
        if current_time - self.last_run < self.cooldown:
            return

        self.last_run = current_time

        print(f"\nRilevata modifica in: {event.src_path}")
        print("Generazione nuovo report...")

        try:
            self.analyzer.generate_report()
            print("Report generato con successo!")

            # Mostra il percorso dell'ultimo report generato
            output_dir = self.analyzer.output_dir
            reports = [f for f in os.listdir(output_dir) if f.startswith('codebase_report')]
            if reports:
                latest_report = max(reports, key=lambda x: os.path.getctime(os.path.join(output_dir, x)))
                print(f"Ultimo report: {os.path.join(output_dir, latest_report)}")

        except Exception as e:
            print(f"Errore durante la generazione del report: {e}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Django Code Analyzer Watcher')
    parser.add_argument('--dir', '-d', default='./', help='Directory principale da monitorare')
    parser.add_argument('--cooldown', '-c', type=int, default=5, help='Tempo minimo tra le analisi (secondi)')
    parser.add_argument('--include', '-i', nargs='+', help='Lista delle directory da includere nel monitoraggio')

    args = parser.parse_args()

    print("Django Code Analyzer Watcher")
    print("============================")

    # Genera un report iniziale
    print("Generazione report iniziale...")
    analyzer = TokenAwareAnalyzer(included_dirs=args.include)
    analyzer.generate_report()

    # Avvia il monitoraggio
    watcher = DjangoWatcher(args.dir, args.cooldown, args.include)
    watcher.run()