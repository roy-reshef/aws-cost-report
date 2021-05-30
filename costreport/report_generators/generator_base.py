from abc import ABC

from costreport.data_container import DataContainer


class ReportGeneratorBase(ABC):
    def __init__(self, data_container: DataContainer, config, filtered_services):
        self.data_container = data_container
        self.config = config
        self.filtered_services = filtered_services

    def generate(self, additional_data_items) -> str:
        """
        return formatted report string
        :param additional_data_items:
        :return:
        """
        raise NotImplementedError("subclass should implement 'generate' function")
