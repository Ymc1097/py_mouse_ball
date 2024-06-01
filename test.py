from mouse import Mouse

mouse1 = Mouse('Logitech G102')
print(mouse1.dev)
mouse1.clear()
mouse1.update(verbose=True)
