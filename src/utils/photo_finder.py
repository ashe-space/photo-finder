from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Type, Union

from PIL import Image
from PIL.Image import MODES
import pathlib
import filetype
import shutil
from dataclasses import dataclass, field
import logging
logger = logging.getLogger()


PHOTO_FORMATS = ('BMP', 'DDS', 'DIB', 'EPS', 'GIF', 'ICNS', 'ICO', 'IM', 'JPEG', 'MSP', 'PCX', 'PNG', 'PPM', 'SGI',
                 'SPIDER', 'TGA', 'TIFF', 'WEBP', 'XBM')
PHOTO_MODES = tuple(MODES)


@dataclass
class FindCopyPhotoResult:
    found: list = field(default_factory=list)
    copied: list = field(default_factory=list)
    not_copied: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def __add__(self, new_result):
        if isinstance(new_result, FindCopyPhotoResult):
            errors = [*self.errors]
            errors.extend(new_result.errors)
            warnings = [*self.warnings]
            warnings.extend(new_result.warnings)
            return FindCopyPhotoResult(
                found=self.found + new_result.found,
                copied=self.copied + new_result.copied,
                not_copied=self.not_copied + new_result.not_copied,
                errors=errors,
                warnings=warnings
            )
        else:
            raise 'Can be add only the same class object'

    def __radd__(self, new_result):
        return self.__add__(new_result)

    def __repr_value(self, name: str, show_if_no: bool = True):
        name_upper = name.upper().replace('_', ' ')
        message = f'NO {name_upper}' if show_if_no else ''
        value = getattr(self, name)
        if value:
            message = f'{name_upper}:'
            if isinstance(value, list):
                for item in value:
                    message += f'\n{item}'
            else:
                message += f' {value}'

        return message


    def repr_warnings(self, show_if_no: bool = True) -> str:
        return self.__repr_value('warnings', show_if_no)

    def repr_errors(self, show_if_no: bool = True) -> str:
        return self.__repr_value('errors', show_if_no)

    def repr_warnings_and_errors(self, show_if_no: bool=True) -> str:
        main_message = self.__repr_value('warnings', show_if_no)
        if main_message:
            main_message += '\n'
        main_message += self.__repr_value('errors', show_if_no)
        return main_message


    def repr_found(self, show_if_no: bool = True) -> str:
        return self.__repr_value('found', show_if_no)

    def repr_copied(self, show_if_no: bool = True) -> str:
        return self.__repr_value('copied', show_if_no)

    def repr_not_copied(self, show_if_no: bool = True) -> str:
        return self.__repr_value('not_copied', show_if_no)

    def repr_short_search(self) -> str:
        main_message = (f'Result: found={len(self.found)}, warnings={len(self.warnings)}, '
                       f'errors={len(self.errors)}')
        if self.warnings or self.errors:
            main_message += f'\n{self.repr_warnings_and_errors(False)}'

        return main_message


    def repr_short_copy(self) -> str:
        main_message = (f'Result: found={len(self.found)}, copied={len(self.copied)}, '
                        f'not_copied={len(self.not_copied)}, warnings={len(self.warnings)}, errors={len(self.errors)}')
        if self.warnings or self.errors:
            main_message += f'\n{self.repr_warnings_and_errors(False)}'

        return main_message

    def repr_detailed_search(self) -> str:
        message = self.repr_short_search()
        if self.found:
            message += f'\n{self.repr_found()}'

        return message


    def repr_detailed_copy(self) -> str:
        message = self.repr_short_copy()
        if self.found:
            message += f'\n{self.repr_found()}'
        if self.copied:
            message += f'\n{self.repr_copied()}'
        if self.not_copied:
            message += f'\n{self.repr_not_copied()}'

        return message


@dataclass(frozen=True)
class PhotoPixelSize:
    width: int = field(default=1)
    height: int = field(default=1)


class PhotoPixelSizeObject(PhotoPixelSize):
    def __init__(self, width: int = 0, height: int = 0):
        if width < 0:
            raise Exception('Width can not be less than 0')
        if height < 0:
            raise Exception('Height can not be less than 0')
        super().__init__(width=width, height=height)


class PhotoRequirements:
    __slots__ = ['_min_photo_sizes', '_photo_modes', '_photo_formats']
    def __init__(self, min_photo_sizes: list = None, photo_modes: Union[list[str], set[str]] = None,
                 photo_formats: Union[list[str], set[str]] = None):
        self._min_photo_sizes = []
        if min_photo_sizes:
            for size in min_photo_sizes:
                if isinstance(size, PhotoPixelSizeObject):
                    self._min_photo_sizes.append(size)
                else:
                    raise Exception(f'Elements of min_photo_sizes should be instance of PhotoPixelSizeObject class')
        self._photo_modes = self.check_photo_modes(photo_modes) if photo_modes is not None else PHOTO_MODES
        self._photo_formats = self.check_photo_formats(photo_formats) if photo_formats is not None else PHOTO_FORMATS

    @property
    def photo_modes(self) -> Union[set, None]:
        return self._photo_modes

    @photo_modes.setter
    def photo_modes(self, modes: Union[list[str], set[str], None]) -> None:
        if modes is None:
            self._photo_modes = PHOTO_MODES
        else:
            self._photo_modes = self.check_photo_modes(modes)

    def set_photo_modes(self, modes: Union[list[str], set[str], None], check: bool = True) -> None:
        if modes is None:
            self._photo_modes = PHOTO_MODES
        else:
            self._photo_modes = self.check_photo_modes(modes) if check else modes

    @property
    def photo_formats(self) -> Union[set, None]:
        return self._photo_formats

    @photo_formats.setter
    def photo_formats(self, formats: Union[list[str], set[str], None]) -> None:
        if formats is None:
            self._photo_formats = PHOTO_FORMATS
        else:
            self._photo_formats = self.check_photo_formats(formats)

    def set_photo_formats(self, formats: Union[list[str], set[str], None], check: bool = True) -> None:
        if formats is None:
            self._photo_formats = PHOTO_FORMATS
        else:
            self._photo_formats = self.check_photo_formats(formats) if check else formats

    @staticmethod
    def _check_requirements_data(data: Union[list[str], set[str]],
                                  possible_data: Union[list[str], set[str], tuple[str,...]], name: str) -> Union[tuple, None]:
        result_data = set()
        for item in data:
            if item in possible_data:
                result_data.add(item)
            else:
                res = False
                for possible_item in possible_data:
                    if possible_item.upper() == item.upper():
                        result_data.add(possible_item)
                        res = True
                        break
                if not res:
                    raise Exception(f'{name}={item} is unknown or unsupported. Supported ones are {possible_data}')
        return tuple(result_data)

    @classmethod
    def check_photo_modes(cls, photo_modes: Union[list[str], set[str]]) -> Union[tuple, None]:
        return cls._check_requirements_data(data=photo_modes, possible_data=PHOTO_MODES, name="Photo mode")

    @classmethod
    def check_photo_formats(cls, photo_formats: Union[list[str], set[str]]) -> Union[tuple, None]:
        return cls._check_requirements_data(data=photo_formats, possible_data=PHOTO_FORMATS, name="Photo format")


    def check_image(self, image: Image.Image) -> bool:
        result = True
        if self._photo_modes and image.mode not in self._photo_modes:
            result = False
        if result and self._photo_formats and image.format not in self._photo_formats:
            result = False
        if result and self._min_photo_sizes:
            according_to_one_of_size = False
            for size in self._min_photo_sizes:
                if image.width >= size.width and image.height >= size.height:
                    according_to_one_of_size = True
                    break
            if not according_to_one_of_size:
                result = False

        return result


def check_image_file_and_copy(path: pathlib.Path, executor_lock: Lock, result: FindCopyPhotoResult,
                                    photo_requirements: PhotoRequirements, copy_dir: pathlib.Path = None):
    try:
        logger.info(f'Start check file {path.absolute()}')
        with Image.open(path) as img:
            img.load()
            if not photo_requirements or photo_requirements.check_image(img):
                with executor_lock:
                    result.found.append(path)
                    logger.info(f'File {path.absolute()} matches requirements')
                if copy_dir is not None:
                    if not pathlib.Path.exists(copy_dir):
                        try:
                            copy_dir.mkdir(parents=True, exist_ok=True)
                        except Exception as e:
                            error_message = (f'Directory {copy_dir.absolute()} was not created, error={repr(e)}. '
                                             f'File {path.absolute()} will not be copied')
                            with executor_lock:
                                result.not_copied.append(path)
                                result.errors.append(error_message)
                            logger.error(error_message)
                            copy_dir_exists = False
                        else:
                            copy_dir_exists = True
                    else:
                        copy_dir_exists = True
                    if copy_dir_exists:
                        save_file_path = pathlib.Path(copy_dir)
                        save_file_path = save_file_path.joinpath(path.name)
                        if not pathlib.Path.exists(save_file_path):
                            try:
                                shutil.copy2(src=path, dst=save_file_path)
                            except Exception as e:
                                error_message = f'File {path.absolute()} will not be copied because of error={repr(e)}'
                                with executor_lock:
                                    result.not_copied.append(path)
                                    result.errors.append(error_message)
                                logger.error(error_message)
                            else:
                                with executor_lock:
                                    result.copied.append(path)
                                logger.info(f'File {path.absolute()} was copied in {save_file_path.absolute()}')
                        else:
                            warning_message = (f'File {path.absolute()} will not be copied because file with name '
                                               f'exists in copy_dir {copy_dir.absolute()}')
                            with executor_lock:
                                result.not_copied.append(path)
                                result.warnings.append(warning_message)
                            logger.warning(warning_message)
            else:
                logger.info(f'File {path.absolute()} does not match requirements')
    except Exception as e:
        error_message = f'Exception error on file "{str(path)}": {repr(e)}'
        with executor_lock:
            result.errors.append(error_message)
        logger.error(error_message)


def _find_and_copy_photo_recursive(executor: ThreadPoolExecutor, executor_lock: Lock, tasks: list, result: FindCopyPhotoResult,
                                   find_dir: pathlib.Path, copy_dir: pathlib.Path = None, recursive: bool = False,
                                   photo_requirements: PhotoRequirements = None) -> None:
    """
        :param executor: ThreadPoolExecutor - executor for checking and copy files
        :param executor_lock: Lock - executor_lock for executor to append results
        :param tasks: list - tasks for checking and copy files
        :param result: FindCopyPhotoResult - result for all
        :param find_dir: pathlib.Path - directory to find photos
        :param copy_dir: pathlib.Path - directory to copy photos
        :param recursive: bool - go to inner directories or not
        :param photo_requirements: PhotoRequirements - requirement to photo to find
    """

    logger.info(f'In directory {find_dir.resolve().absolute()}')
    if find_dir == copy_dir:
        warning_message = f'find_dir "{find_dir}" and copy_dir "{copy_dir}" are the same, find_dir will be skipped'
        with executor_lock:
            result.warnings.append(warning_message)
        logger.warning(warning_message)
        return

    for item in find_dir.iterdir():
        if item.is_dir() and recursive:
            if item != copy_dir:
                new_copy_dir = pathlib.Path(copy_dir).joinpath(item.name)
                _find_and_copy_photo_recursive(executor=executor, executor_lock=executor_lock, tasks=tasks, result=result,
                                               find_dir=item, copy_dir=new_copy_dir, recursive=recursive,
                                               photo_requirements=photo_requirements)
            else:
                warning_message = (f'"Directory {item}" and copy_dir "{copy_dir}" are the same, '
                                   f'this directory will be skipped')
                with executor_lock:
                    result.warnings.append(warning_message)
                logger.warning(warning_message)
        elif item.is_file() and filetype.is_image(item):
            tasks.append(executor.submit(check_image_file_and_copy, path=item, result=result,
                                   executor_lock=executor_lock, copy_dir=copy_dir, photo_requirements=photo_requirements))




# find photo and copy it with recursive call
def find_and_copy_photo(find_dir: pathlib.Path, copy_dir: pathlib.Path = None, recursive: bool = False,
                        photo_requirements: PhotoRequirements = None,
                        result: FindCopyPhotoResult = None) -> FindCopyPhotoResult:
    """
        :param find_dir: pathlib.Path - directory to find photos
        :param copy_dir: pathlib.Path - directory to copy photos
        :param recursive: bool - go to inner directories or not
        :param photo_requirements: PhotoRequirements - requirement to photo to find
        :param result: FindCopyPhotoResult - to get result even if will be some exception
        :return: FindCopyPhotoResult - dataclass with found, copied, errors and warnings fields - result of function
    """
    if result is None:
        result = FindCopyPhotoResult()

    if not pathlib.Path.exists(find_dir):
        result.errors.append(f'find_dir "{find_dir}" does not exist')
    elif not find_dir.is_dir():
        result.errors.append(f'find_dir "{find_dir}" is not directory')

    if copy_dir is not None:
        if not pathlib.Path.exists(copy_dir):
            result.errors.append(f'copy_dir "{copy_dir}" does not exist')
        elif not copy_dir.is_dir():
            result.errors.append(f'copy_dir "{copy_dir}" is not directory')

    if result.errors:
        return result

    executor_lock = Lock()
    tasks = []
    with ThreadPoolExecutor() as executor:
        _find_and_copy_photo_recursive(tasks=tasks, executor=executor, executor_lock=executor_lock, result=result,
                                       find_dir=find_dir, copy_dir=copy_dir,
                                       recursive=recursive, photo_requirements=photo_requirements)


    return result
