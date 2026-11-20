import { http } from "./client";

export const model = {
    summary: async () => (await http.get("/model")).data,
    /** {evaluated, model, thresholds, metrics:{test,roc,calibration,comparison,cross_validation,per_source,per_generator,errors,robustness,ood,datasets,leakage_check}, notice} */
    evaluation: async () => (await http.get("/model/evaluation")).data,
    /** {app:'ok', ml:{status, model_loaded}} */
    health: async () => (await http.get("/health")).data,
};
