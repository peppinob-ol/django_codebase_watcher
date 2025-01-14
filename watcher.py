# watch_analyzer.py
# Copyright (c) 2024 Giuseppe Birardi
# Licensed under the MIT License - see LICENSE file for details

import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dj_context_print import TokenAwareAnalyzer  # il nostro analyzer precedente


class DjangoWatcher:
    def __init__(self, directory_to_watch='./', cooldown=5):
        self.DIRECTORY_TO_WATCH = directory_to_watch
        self.cooldown = cooldown  # Tempo minimo tra le analisi
        self.observer = Observer()
        self.last_run = 0

    def run(self):
        event_handler = DjangoHandler(self.cooldown)
        self.observer.schedule(event_handler, self.DIRECTORY_TO_WATCH, recursive=True)
        self.observer.start()
        print(f"Monitoraggio avviato nella directory: {self.DIRECTORY_TO_WATCH}")
        print("Premi Ctrl+C per terminare...")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nArresto del monitoraggio...")
            self.observer.stop()
        self.observer.join()


class DjangoHandler(FileSystemEventHandler):
    def __init__(self, cooldown):
        self.cooldown = cooldown
        self.last_run = 0
        self.relevant_extensions = {'.py', '.html', '.js', '.css'}
        self.analyzer = TokenAwareAnalyzer()

    def on_modified(self, event):
        # Verifica se il file è rilevante
        if event.is_directory:
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
            reports = [f for f in os.listdir(output_dir) if f.startswith('token_report_')]
            if reports:
                latest_report = max(reports, key=lambda x: os.path.getctime(os.path.join(output_dir, x)))
                print(f"Ultimo report: {os.path.join(output_dir, latest_report)}")

        except Exception as e:
            print(f"Errore durante la generazione del report: {e}")


if __name__ == '__main__':
    # Configurazione del watcher
    directory_to_watch = './'  # Directory del progetto Django
    cooldown_seconds = 5  # Tempo minimo tra le analisi

    print("Django Code Analyzer Watcher")
    print("============================")

    # Genera un report iniziale
    print("Generazione report iniziale...")
    analyzer = TokenAwareAnalyzer()
    analyzer.generate_report()

    # Avvia il monitoraggio
    watcher = DjangoWatcher(directory_to_watch, cooldown_seconds)
    watcher.run()