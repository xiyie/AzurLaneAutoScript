from module.base.decorator import Config
from module.base.timer import Timer
from module.base.utils import *
from module.exception import ScriptError
from module.logger import logger
from module.ocr.ocr import Ocr
from module.os.assets import *
from module.os.globe_zone import Zone
from module.os_handler.map_order import MapOrderHandler
from module.os_handler.mission import MissionHandler
from module.os_handler.port import PortHandler
from module.os_handler.storage import StorageHandler


class OSMapOperation(MapOrderHandler, MissionHandler, PortHandler, StorageHandler):
    zone: Zone

    def is_meowfficer_searching(self):
        """
        Returns:
            bool:

        Page:
            in: IN_MAP
        """
        return self.appear(MEOWFFICER_SEARCHING, offset=(10, 10))

    def get_meowfficer_searching_percentage(self):
        """
        Returns:
            float: 0 to 1.

        Pages:
            in: IN_MAP, is_meowfficer_searching == True
        """
        return color_bar_percentage(
            self.device.image, area=MEOWFFICER_SEARCHING_PERCENTAGE.area, prev_color=(74, 223, 255))

    @Config.when(SERVER='en')
    def get_zone_name(self):
        # For EN only
        from string import whitespace
        ocr = Ocr(MAP_NAME, lang='cnocr', letter=(214, 235, 235), threshold=96, name='OCR_OS_MAP_NAME')
        name = ocr.ocr(self.device.image)
        name = name.translate(dict.fromkeys(map(ord, whitespace)))
        name = name.lower()
        if '-' in name:
            name = name.split('-')[0]
        if 'é' in name:  # Méditerranée name maps
            name = name.replace('é', 'e')
        if 'nvcity' in name:  # NY City Port read as 'V' rather than 'Y'
            name = 'nycity'
        return name

    @Config.when(SERVER='jp')
    def get_zone_name(self):
        # For JP only
        ocr = Ocr(MAP_NAME, lang='jp', letter=(214, 231, 255), threshold=127, name='OCR_OS_MAP_NAME')
        name = ocr.ocr(self.device.image)
        # Remove '安全海域' or '秘密海域' at the end of jp ocr.
        name = name.rstrip('安全海域秘密海域')
        # Kanji '一' and '力' are not used, while Katakana 'ー' and 'カ' are misread as Kanji sometimes.
        # Katakana 'ペ' may be misread as Hiragana 'ぺ'.
        name = name.replace('一', 'ー').replace('力', 'カ').replace('ぺ', 'ペ')
        return name

    @Config.when(SERVER='tw')
    def get_zone_name(self):
        # For JP only
        ocr = Ocr(MAP_NAME, lang='tw', letter=(214, 231, 255), threshold=127, name='OCR_OS_MAP_NAME')
        name = ocr.ocr(self.device.image)
        # Remove '安全海域' or '隱秘海域' at the end of tw ocr.
        name = name.rstrip('安全海域隱秘海域一')
        return name

    @Config.when(SERVER=None)
    def get_zone_name(self):
        # For CN only
        ocr = Ocr(MAP_NAME, lang='cnocr', letter=(214, 231, 255), threshold=127, name='OCR_OS_MAP_NAME')
        name = ocr.ocr(self.device.image)
        if '-' in name:
            name = name.split('-')[0]
        else:
            name = name.rstrip('安全海域-')
        return name

    def get_current_zone(self):
        """
        Returns:
            Zone:
        """
        if not self.is_in_map():
            logger.warning('Trying to get zone name, but not in OS map')
            raise ScriptError('Trying to get zone name, but not in OS map')

        name = self.get_zone_name()
        logger.info(f'Map name processed: {name}')
        self.zone = self.name_to_zone(name)
        logger.attr('Zone', self.zone)
        return self.zone

    def is_in_special_zone(self):
        """
        Returns:
            bool: If in an obscure zone, abyssal zone, or stronghold.
        """
        return self.appear(MAP_EXIT, offset=(20, 20))

    def map_exit(self, skip_first_screenshot=True):
        """
        Exit from an obscure zone, abyssal zone, or stronghold.

        Args:
            skip_first_screenshot:

        Pages:
            in: is_in_map
            out: is_in_map, zone that you came from
        """
        logger.hr('Map exit')
        confirm_timer = Timer(1, count=2)
        changed = False
        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            # End
            if changed and self.is_in_map():
                if confirm_timer.reached():
                    break
            else:
                confirm_timer.reset()

            if self.appear_then_click(MAP_EXIT, offset=(20, 20), interval=5):
                continue
            if self.handle_popup_confirm('MAP_EXIT'):
                self.interval_reset(MAP_EXIT)
                continue
            if self.handle_map_event():
                self.interval_reset(MAP_EXIT)
                changed = True
                continue

        self.get_current_zone()
