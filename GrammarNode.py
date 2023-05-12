class GrammarNode:
    'Узел дерева грамматики'
    def __init__(self):
        self.value = [] #значение узла - левая часть правила (аккорды)
        self.nextNodes = {}  #словарь, ключ - возможная продукция (аккорд), значение - следующий узел, может быть пуст (None)
