import os


class PathBuilder(object):

    Instance = None

    @classmethod
    def get(cls):

        if cls.Instance is None:
            cls.Instance = StandardPathBuilder()

        return cls.Instance

    @classmethod
    def get_path(cls, file_name, folder_relative_to_root=None):
        return cls.get().get_path(file_name, folder_relative_to_root)


class StandardPathBuilder(object):

    def get_path(self, file_name, folder_relative_to_root=None):

        path = self.get_base_folder()

        if folder_relative_to_root is not None:
            path = os.path.join(path, folder_relative_to_root)

        path = os.path.join(path, file_name)

        return path

    def get_base_folder(self):
        return os.getcwd()
