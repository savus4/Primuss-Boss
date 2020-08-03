import json
import os

class Results:
    results = dict()
    results_path = str()
    results_file = "results.json"
    changed_results = dict()
    changes_since_last_update = bool()
    last_fetch_failed = bool()
    subject_abbreviations = {"Digitale Signalverarbeitung": "DS",
                             "Automotive-Projekt": "VR",
                             "Informations- und Medienkompetenz (PLV3)": "PLV3",
                             "Praktikum Digitale Signalverarbeitung": "DSP",
                             "Sicherheitskritische Systeme": "SKS",
                             "Sensoren und Aktoren für Automotive-Anwendungen": "SA"}

    def __init__(self, results_path):
        self.results_path = os.path.join(results_path, self.results_file)
        if os.path.exists(self.results_path):
            with open(self.results_path) as json_file:
                self.results = json.load(json_file)
        else:
            (folder_part, _) = os.path.split(results_path)
            os.makedirs(folder_part, exist_ok=True)

    def refresh_grades(self, new_grades):
        self.check_for_changes(new_grades)
        if self.changes_since_last_update:
            self.__save_results(new_grades)
        return self.changes_since_last_update

    def check_for_changes(self, current_data):
        self.changed_results = dict()
        self.changes_since_last_update = False
        if len(current_data) != 0:
            # check for first time use
            if len(self.results) != 0:
                self.last_fetch_failed = False
                for subject in current_data:
                    for cachedSubject in self.results:
                        if subject == cachedSubject and current_data[subject] != self.results[cachedSubject]:
                            self.changed_results[subject] = current_data[subject]
                            self.changes_since_last_update = True
            else:
                self.__save_results(current_data)
        else:
            self.last_fetch_failed = True

    def __save_results(self, new_results):
        self.results = new_results
        with open(self.results_path, "w") as json_file:
            json.dump(new_results, json_file)

    def as_string(self):
        results_str = str()
        for key in self.results:
            results_str += str(key) + ": " + self.results[key] + "\n\n"
        return results_str
