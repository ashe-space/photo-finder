# photo-finder
### This is utility for searching and copying photos that match the specified parameters

For example, there are a lot of photos from mobile phone, some of which you want to post on platforms that require special sizes, like Cavayar. 
This utility will help you find and copy photos to a separate folder according to the specified parameters.

## HOW TO USE

### Start: 
- __pip install .__
- __photo-finder__ *[OPTIONS]* __COMMAND__ *[COMMAND-ARGS] [COMMAND-OPTIONS]*...

#### Options:
- __-d, --find_dir__

    (DIRECTORY) Directory where to search photos or current by default


- __-r, --recursive__           

    (FLAG) Search in inner directories recursively


- __-m, --photo_modes__

    (TEXT) Search photo with selected mode or modes  
    By default any of ('1', 'CMYK', 'F', 'HSV', 'I', 'L', 'LAB', 'P', 'RGB', 'RGBA', 'RGBX', 'YCbCr')
    use MODE for one and MODE_1,MODE_2,... for several


- __-f, --photo_formats__ 

    (TEXT) Search photo with selected format or formats  
    By default any of ('BMP', 'DDS', 'DIB', 'EPS', 'GIF', 'ICNS', 'ICO', 'IM', 'JPEG', 'MSP', 'PCX', 'PNG', 'PPM', 'SGI', 'SPIDER', 'TGA', 'TIFF', 'WEBP', 'XBM'))  
    use FORMAT for one and FORMAT_1,FORMAT_2,... for several


- __-s, --min_sizes__ 

    (TEXT) Set size in format width:height for one size or width:height,width:height,... for several  
    Maximum 10 sizes from 0:0 to 999999:999999


- __-a, --add_reverse_sizes__   

    (FLAG) Add reverse min sizes


- __-e, --extended_result__     

    (FLAG) Show extended result


- __-l, --with_logs__           

    (FLAG) Show info logs


- __--help__                    

    Show help

### Commands:
#### search
- ##### Options
  - __--help__                    

      Show help
#### copy
- ##### Arguments
  - __COPY_DIR__

     (DIRECTORY) Directory to copy found files
- ##### Options
  - __--help__                    

     Show help

