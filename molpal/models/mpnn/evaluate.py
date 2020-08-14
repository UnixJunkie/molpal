import logging
from typing import Callable, List

from torch import nn

from .predict import predict
from chemprop.data import MoleculeDataLoader, StandardScaler

def evaluate_predictions(
    preds: List[List[float]], targets: List[List[float]],
    num_tasks: int, metric_func: Callable, dataset_type: str,
    logger: logging.Logger = None) -> List[float]:
    """
    Evaluates predictions using a metric function and filtering out invalid targets.

    :param preds: A list of lists of shape (data_size, num_tasks) with model predictions.
    :param targets: A list of lists of shape (data_size, num_tasks) with targets.
    :param num_tasks: Number of tasks.
    :param metric_func: Metric function which takes in a list of targets and a list of predictions.
    :param dataset_type: Dataset type.
    :param logger: Logger.
    :return: A list with the score for each task based on `metric_func`.
    """
    info = logger.info if logger is not None else print

    if len(preds) == 0:
        return [float('nan')] * num_tasks

    # Filter out empty targets
    # valid_preds and valid_targets have shape (num_tasks, data_size)
    valid_preds = [[]] * num_tasks
    valid_targets = [[]] * num_tasks

    for j in range(num_tasks):
        for i in range(len(preds)):
            if targets[i][j] is None:
                continue

            valid_preds[j].append(preds[i][j])
            valid_targets[j].append(targets[i][j])

    # Compute metric
    results = []
    for preds, targets in zip(valid_preds, valid_targets):
        # if all targets or preds are identical classification will crash
        if dataset_type == 'classification':
            if all(t == 0 for t in targets) or all(targets):
                info('Warning: Found a task with targets all 0s or all 1s')
                results.append(float('nan'))
                continue
            if all(p == 0 for p in preds) or all(preds):
                info('Warning: Found a task with predictions all 0s or all 1s')
                results.append(float('nan'))
                continue

        if len(targets) == 0:
            continue

        # if dataset_type == 'multiclass':
        #     results.append(metric_func(valid_targets[i], valid_preds[i], labels=list(range(len(valid_preds[i][0])))))
        # else:

        results.append(metric_func(targets, preds))

    return results

def evaluate(model: nn.Module, data_loader: MoleculeDataLoader, num_tasks: int,
             metric_func: Callable, dataset_type: str,
             scaler: StandardScaler = None,
             logger: logging.Logger = None) -> List[float]:
    """
    Evaluates an ensemble of models on a dataset.

    :param model: A model.
    :param data_loader: A MoleculeDataLoader.
    :param num_tasks: Number of tasks.
    :param metric_func: Metric function which takes in a list of targets and a list of predictions.
    :param dataset_type: Dataset type.
    :param scaler: A StandardScaler object fit on the training targets.
    :param logger: Logger.
    :return: A list with the score for each task based on `metric_func`.
    """
    def batch_graphs(data_loader):
        for batch in data_loader:
            yield batch.batch_graph()

    preds = predict(model=model, batch_graphs=batch_graphs(data_loader), 
                    scaler=scaler)
                    
    results = evaluate_predictions(
        preds=preds, targets=data_loader.targets, num_tasks=num_tasks,
        metric_func=metric_func, dataset_type=dataset_type, logger=logger
    )

    return results
    