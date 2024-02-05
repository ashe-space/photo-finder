import pathlib
import re
import click

from utils import FindCopyPhotoResult, PhotoPixelSizeObject, PhotoRequirements, find_and_copy_photo, PHOTO_FORMATS, \
    PHOTO_MODES
import logging
logger = logging.getLogger()


def size_type(ctx, param, value):
    if value is None or value == '':
        min_sizes = None
    else:
        pattern = r'^([0-9]{1,6}:[0-9]{1,6})(,([0-9]{1,6}:[0-9]{1,6})){0,9}$'
        check_result = re.match(pattern, value)
        if not check_result:
            raise click.BadParameter('Incorrect sizes pattern. Set size in format width:height for one size '
                                     'or width:height,width:height,... for several '
                                     '(maximum 10 sizes from 0:0 to 999999:999999)')

        min_sizes = []
        sizes_list = value.split(",")
        for size_str in sizes_list:
            one_size_list = size_str.split(":")
            min_sizes.append(PhotoPixelSizeObject(width=int(one_size_list[0]), height=int(one_size_list[1])))
    return min_sizes


def photo_mode(ctx, param, value):
    if value is None or value == '':
        modes = PHOTO_MODES
    else:
        modes = value.split(",")
        try:
            modes = PhotoRequirements.check_photo_modes(modes)
        except Exception as e:
            raise click.BadParameter(str(e))
    return modes


def photo_format(ctx, param, value):
    if value is None or value == '':
        formats = PHOTO_FORMATS
    else:
        formats = value.split(",")
        try:
            formats = PhotoRequirements.check_photo_formats(formats)
        except Exception as e:
            raise click.BadParameter(str(e))
    return formats


@click.group()
@click.option('-d', '--find_dir', default=None, type=click.Path(dir_okay=True, file_okay=False, exists=True),
              help='Directory where to search photos or current by default')
@click.option('-r', '--recursive', is_flag=True, help='Search in inner directories recursively')
@click.option('-m', '--photo_modes', default=None, type=click.UNPROCESSED, callback=photo_mode,
              help=f'Search photo with selected mode or modes (default any of {PHOTO_MODES}) - '
                   f'use MODE for one and MODE_1,MODE_2,... for several')
@click.option('-f', '--photo_formats', default=None, type=click.UNPROCESSED, callback=photo_format,
              help=f'Search photo with selected format or formats (default any of {PHOTO_FORMATS}) - '
                   f'use FORMAT for one and FORMAT_1,FORMAT_2,... for several')
@click.option('-s', '--min_sizes', type=click.UNPROCESSED, callback=size_type, default=None,
              show_default=True, help='Set size in format width:height for one size or width:height,width:height,... '
                                      'for several (maximum 10 sizes from 0:0 to 999999:999999)')
@click.option('-a', '--add_reverse_sizes', is_flag=True, help='Add reverse min sizes')
@click.option('-e', '--extended_result', is_flag=True, help='Show extended result')
@click.option('-l', '--with_logs', is_flag=True, help='Show info logs')
@click.pass_context
def photo_finder(context, find_dir, recursive, photo_modes, photo_formats, min_sizes, add_reverse_sizes, extended_result,
                 with_logs):
    if with_logs:
        logger.setLevel(logging.INFO)
    context.ensure_object(dict)
    result = FindCopyPhotoResult()
    context.obj['result'] = result
    try:
        context.obj['find_dir'] = pathlib.Path(find_dir) if find_dir else pathlib.Path.cwd()
        context.obj['recursive'] = recursive
        context.obj['extended_result'] = extended_result
        min_photo_sizes = []
        if min_sizes:
            for size_item in min_sizes:
                min_photo_sizes.append(size_item)
                if add_reverse_sizes:
                    min_photo_sizes.append(PhotoPixelSizeObject(width=size_item.height, height=size_item.width))

        # set photo requirements
        photo_requirements = PhotoRequirements(min_photo_sizes=min_photo_sizes)
        photo_requirements.set_photo_modes(photo_modes, False)
        photo_requirements.set_photo_formats(photo_formats, False)
        context.obj['photo_requirements'] = photo_requirements

    except Exception as e:
        result.errors.append(f'Exception error: {repr(e)}')


@photo_finder.command()
@click.pass_context
def search(context):
    click.echo('\nStart search')
    result = context.obj['result']
    if not result.errors:
        try:
            res = find_and_copy_photo(find_dir=context.obj['find_dir'], recursive=context.obj['recursive'],
                                      photo_requirements=context.obj['photo_requirements'])
            result = context.obj['result'] + res
        except Exception as e:
            result.errors.append(f'Exception error: {repr(e)}')
    click.echo(f'End search\n{result.repr_detailed_search() if context.obj["extended_result"] else result.repr_short_search()}\n')


@photo_finder.command()
@click.argument('copy_dir', type=click.Path(dir_okay=True, file_okay=False, exists=True))
@click.pass_context
def copy(context, copy_dir):
    click.echo('\nStart copy')
    result = context.obj['result']
    if not result.errors:
        try:
            copy_dir = pathlib.Path(copy_dir)
            find_and_copy_photo(find_dir=context.obj['find_dir'], copy_dir=copy_dir,
                                recursive=context.obj['recursive'],
                                photo_requirements=context.obj['photo_requirements'],
                                result=result)
        except Exception as e:
            result.errors.append(f'Exception error: {repr(e)}')
    click.echo(f'End copy\n{result.repr_detailed_copy() if context.obj["extended_result"] else result.repr_short_copy()}\n')


def main():
    logging.basicConfig(format=u'%(asctime)s - %(levelname)s - %(filename)s[LINE:%(lineno)d] - %(message)s')
    logger.setLevel(logging.CRITICAL)
    photo_finder()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()
