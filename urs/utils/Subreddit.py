#===============================================================================
#                             Subreddit Scraping
#===============================================================================
from colorama import Fore, init, Style

from . import Cli, Export, Global, Titles, Validation
from .Logger import LogExport, LogScraper

### Automate sending reset sequences to turn off color changes at the end of 
### every print.
init(autoreset = True)

### Global variables
categories = Global.categories
options = Global.options
short_cat = Global.short_cat

class CheckSubs():
    """
    Function for checking if Subreddit(s) exist. Print invalid Subreddits if
    applicable.
    """

    ### Check if Subreddits exist and list invalid Subreddits if applicable
    @staticmethod
    def confirm_subs(parser, reddit, s_t, sub_list):
        print("\nChecking if Subreddit(s) exist...")
        subs, not_subs = Validation.Validation().existence(s_t[0], sub_list, 
            parser, reddit, s_t)
        if not_subs:
            print(Fore.YELLOW + Style.BRIGHT + 
                "\nThe following Subreddits were not found and will be skipped:")
            print(Fore.YELLOW + Style.BRIGHT + "-" * 60)
            print(*not_subs, sep = "\n")

        if not subs:
            print(Fore.RED + Style.BRIGHT + "\nNo Subreddits to scrape!")
            print(Fore.RED + Style.BRIGHT + "\nExiting.\n")
            quit()

        return subs

class PrintConfirm():
    """
    Functions for printing Subreddit settings and confirm settings.
    """

    ### Print each Subreddit setting.
    @staticmethod
    def _print_each(args, s_master):
        for sub, settings in s_master.items():
            for each in settings:
                cat_i = short_cat.index(each[0].upper()) if not args.basic \
                    else each[0]
                specific = each[1]
                
                print("\n{:<25}{:<17}{:<30}".format(sub, categories[cat_i], specific))

    ### Print scraping details for each Subreddit.
    @staticmethod
    def print_settings(args, s_master):
        print(Style.BRIGHT + "\n------------------Current settings for each Subreddit-------------------")
        print(Style.BRIGHT + "\n{:<25}{:<17}{:<30}".format("Subreddit", "Category", 
                "Number of results / Keyword(s)"))
        print(Style.BRIGHT + "-" * 72)

        PrintConfirm._print_each(args, s_master)

    ### Confirm scraping options.
    @staticmethod
    def confirm_settings():
        while True:
            try:
                confirm = input("\nConfirm options? [Y/N] ").strip().lower()

                if confirm == options[0]:
                    return confirm
                elif confirm == options[1]:
                    break
                elif confirm not in options:
                    raise ValueError
            except ValueError:
                print("Not an option! Try again.")

class GetPostsSwitch():
    """
    Implementing Pythonic switch case to determine which Subreddit category to
    get results from.
    """

    ### Initialize objects that will be used in class methods.
    def __init__(self, search_for, subreddit):
        self._hot = subreddit.hot(limit = int(search_for))
        self._new = subreddit.new(limit = int(search_for))
        self._controversial = subreddit.controversial(limit = int(search_for))
        self._top = subreddit.top(limit = int(search_for))
        self._rising = subreddit.rising(limit = int(search_for))

        self._switch = {
            0: self._hot,
            1: self._new,
            2: self._controversial,
            3: self._top,
            4: self._rising
        }

    ### Return a command based on the chosen category.
    def scrape_sub(self, index):
        return self._switch.get(index)

class GetPosts():
    """
    Functions for getting posts from a Subreddit.
    """

    ### Return PRAW ListingGenerator for searching keywords.
    @staticmethod
    def _collect_search(search_for, sub, subreddit):
        print((Style.BRIGHT + "\nSearching posts in r/%s for '%s'...") % 
            (sub, search_for))

        return subreddit.search("%s" % search_for)

    ### Return PRAW ListingGenerator for all other categories.
    @staticmethod
    def _collect_others(args, cat_i, search_for, sub, subreddit):
        category = categories[short_cat.index(cat_i)] if args.subreddit \
            else categories[cat_i]
        index = short_cat.index(cat_i) if args.subreddit else cat_i
            
        print(Style.BRIGHT + ("\nProcessing %s %s results from r/%s...") % 
            (search_for, category, sub))
        
        return GetPostsSwitch(search_for, subreddit).scrape_sub(index)

    ### Get Subreddit posts and return the PRAW ListingGenerator.
    @staticmethod
    def get(args, reddit, sub, cat_i, search_for):
        subreddit = reddit.subreddit(sub)

        return GetPosts._collect_search(search_for, sub, subreddit) \
            if cat_i == short_cat[5] or cat_i == 5 \
            else GetPosts._collect_others(args, cat_i, search_for, sub, subreddit)

class SortPosts():
    """
    Functions for sorting posts based on the export option.
    """

    ### Initialize objects that will be used in class methods.
    def __init__(self):
        self._convert_time = Global.convert_time
        self._titles = ["Title", "Flair", "Date Created", "Upvotes", "Upvote Ratio", 
                        "ID", "Edited?", "Is Locked?", "NSFW?", "Is Spoiler?", 
                        "Stickied?", "URL", "Comment Count", "Text"]

    ### Initialize dictionary depending on export option.
    def _initialize_dict(self, args):
        return Global.make_list_dict(self._titles) if args.csv else dict()

    ### Fix "Edited?" date.
    def _fix_edit_date(self, post):
        return str(post.edited) if str(post.edited).isalpha() \
                else str(self._convert_time(post.edited))

    ### Get post data.
    def _get_data(self, post):
        edited = self._fix_edit_date(post)
        post_data = [post.title, post.link_flair_text, self._convert_time(post.created), 
            post.score, post.upvote_ratio, post.id, edited, post.locked, 
            post.over_18, post.spoiler, post.stickied, post.url, 
            post.num_comments, post.selftext]

        return post_data

    ### Append data to overview dictionary for CSV export.
    def _csv_format(self, overview, post_data):
        for title, data in zip(self._titles, post_data):
                overview[title].append(data)

    ### Append data to overview dictionary for JSON export.
    def _json_format(self, count, overview, post_data):
        overview["Post %s" % count] = {
            title:value for title, value in zip(self._titles, post_data)}
    
    ### Sort collected dictionary based on export option.
    def sort(self, args, collected):
        print("\nThis may take a while. Please wait.")

        overview = self._initialize_dict(args)

        if args.csv:
            for post in collected:
                post_data = self._get_data(post)
                self._csv_format(overview, post_data)
        elif args.json:
            for count, post in enumerate(collected, start = 1):
                post_data = self._get_data(post)
                self._json_format(count, overview, post_data)

        return overview

class GetSortWrite():
    """
    Functions to get, sort, then write scraped Subreddit posts to CSV or JSON.
    """

    ### Initialize objects that will be used in class methods.
    def __init__(self):
        self._eo = Global.eo

    ### Get and sort posts.
    def _get_sort(self, args, cat_i, each, reddit, search_for, sub):
        collected = GetPosts.get(args, reddit, sub, cat_i, search_for)        
        return SortPosts().sort(args, collected)

    ### Export to either CSV or JSON.
    def _determine_export(self, args, f_name, overview):
        Export.Export.export(f_name, self._eo[1], overview) if args.json else \
            Export.Export.export(f_name, self._eo[0], overview)

    ### Set print length depending on string length.
    def _print_confirm(self, args, sub):
        confirmation = "\nJSON file for r/%s created." % sub if args.json \
            else "\nCSV file for r/%s created." % sub
        print(Style.BRIGHT + Fore.GREEN + confirmation)
        print(Style.BRIGHT + Fore.GREEN + "-" * (len(confirmation) - 1))

    ### Write posts.
    def _write(self, args, cat_i, overview, search_for, sub):
        f_name = Export.NameFile().r_fname(args, cat_i, search_for, sub)
        self._determine_export(args, f_name, overview)
        self._print_confirm(args, sub)

    ### Get, sort, then write.
    def gsw(self, args, reddit, s_master):
        for sub, settings in s_master.items():
            for each in settings:
                cat_i = each[0].upper() if not args.basic else each[0]
                search_for = each[1]

                overview = self._get_sort(args, cat_i, each, reddit, search_for, sub)
                self._write(args, cat_i, overview, search_for, sub)

class RunSubreddit():
    """
    Run the Subreddit scraper.
    """

    ### Create settings for each user input.
    @staticmethod
    def _create_settings(args, parser, reddit, s_t):
        sub_list = Cli.GetScrapeSettings().create_list(args, s_t[0])
        subs = CheckSubs.confirm_subs(parser, reddit, s_t, sub_list)
        s_master = Global.make_list_dict(subs)
        Cli.GetScrapeSettings().get_settings(args, s_master, s_t[0])

        return s_master

    ### Print the confirm screen if the user did not specify the `-y` flag.
    @staticmethod
    @LogScraper.log_cancel
    def _confirm_write(args, reddit, s_master):
        PrintConfirm.print_settings(args, s_master)
        confirm = PrintConfirm.confirm_settings()

        if confirm == options[0]:
            GetSortWrite().gsw(args, reddit, s_master)
        else:
            raise KeyboardInterrupt

    ### Skip or print Subreddit scraping settings if the `-y` flag is entered.
    ### Then write or quit scraper.
    @staticmethod
    def _write_file(args, reddit, s_master):
        if args.y:
            GetSortWrite().gsw(args, reddit, s_master)
        else:
            RunSubreddit._confirm_write(args, reddit, s_master)

    ### Run Subreddit scraper.
    @staticmethod
    @LogExport.log_export
    @LogScraper.scraper_timer(Global.s_t[0])
    def run(args, parser, reddit, s_t):
        Titles.Titles.r_title()

        s_master = RunSubreddit._create_settings(args, parser, reddit, s_t)
        RunSubreddit._write_file(args, reddit, s_master)
