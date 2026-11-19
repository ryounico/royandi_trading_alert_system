
import sys
from dotenv import load_dotenv

load_dotenv()

from rta.bot import main, once_main

if __name__ == "__main__":
    if "--once" in sys.argv:
        once_main()
    else:
        main()
