import ConfigParser

class FruitConfigParser(ConfigParser.SafeConfigParser):
    def get_all(self, section, option):
        results = []
        index = 1

        try:
            while True:
                results.append(self.get(section, "%s.%d" % (option, index)))
                index += 1

        except ConfigParser.NoOptionError:
            return results


    # Don't transform option names to lower case:
    def optionxform(self, opt):
        return opt

    def getfloats(self, section, option):
        values = self.get(section, option)
        return [float(f) for f in values.split(" ")]

config = FruitConfigParser()
